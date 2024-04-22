"""
"""

import copy
import shutil
from pathlib import Path

import pandas as pd
import paramiko
import pytest
import ssh_test_utils
import test_utils
from base import BaseTest

from datashuttle.utils import ssh

TEST_SSH = ssh_test_utils.get_test_ssh()

PARAM_SUBS = [
    ["all"],
    ["all_sub"],
    ["all_non_sub"],
    ["sub-001"],
    ["sub-003_date-20231901"],
    ["sub-002", "all_non_sub"],
]
PARAM_SES = [
    ["all"],
    ["all_non_ses"],
    ["all_ses"],
    ["ses-001"],
    ["ses-002_random-key"],
    ["all_non_ses", "ses-001"],
]
PARAM_DATATYPE = [
    ["all"],
    ["all_non_datatype"],
    ["all_datatype"],
    ["behav"],
    ["ephys"],
    ["anat"],
    ["funcimg"],
    ["anat", "behav", "all_non_datatype"],
]


class TestFileTransfer(BaseTest):

    # ----------------------------------------------------------------------------------
    # Test File Transfer - All Options
    # ----------------------------------------------------------------------------------

    @pytest.mark.parametrize("sub_names", PARAM_SUBS)
    @pytest.mark.parametrize("ses_names", PARAM_SES)
    @pytest.mark.parametrize("datatype", PARAM_DATATYPE)
    @pytest.mark.parametrize("upload_or_download", ["upload", "download"])
    def test_combinations_filesystem_transfer(
        self,
        pathtable_and_project,
        sub_names,
        ses_names,
        datatype,
        upload_or_download,
    ):
        """
        Test many combinations of possible file transfer commands. The
        entire test project is created in the original `local_path`
        and subset of it is uploaded and tested against. To test
        upload vs. download, the `local_path` and `central_path`
        locations are swapped.
        """
        pathtable, project = pathtable_and_project

        # Transfer the data, swapping the paths to move a subset of
        # files from the already set up directory to a new directory
        # using upload or download.
        transfer_function = test_utils.handle_upload_or_download(
            project,
            upload_or_download,
            transfer_method="custom",
            swap_last_folder_only=False,
        )[0]

        transfer_function(
            "rawdata", sub_names, ses_names, datatype, init_log=False
        )

        if upload_or_download == "download":
            test_utils.swap_local_and_central_paths(
                project, swap_last_folder_only=False
            )

        expected_transferred_paths = self.get_expected_transferred_paths(
            pathtable, sub_names, ses_names, datatype
        )

        # Check what paths were actually moved
        # (through the local filesystem), and test
        path_to_search = (
            self.central_from_local(project.cfg["local_path"]) / "rawdata"
        )
        all_transferred = path_to_search.glob("**/*")

        paths_to_transferred_files = list(
            filter(Path.is_file, all_transferred)
        )

        paths_to_transferred_files = self.remove_path_before_rawdata(
            paths_to_transferred_files
        )

        assert sorted(paths_to_transferred_files) == sorted(
            expected_transferred_paths
        )

        # Teardown here, because we have session scope.
        try:
            shutil.rmtree(self.central_from_local(project.cfg["local_path"]))
        except FileNotFoundError:
            pass

    @pytest.mark.skipif("not TEST_SSH", reason="TEST_SSH is false")
    @pytest.mark.parametrize(
        "sub_names", [["all"], ["all_non_sub", "sub-002"]]
    )
    @pytest.mark.parametrize(
        "ses_names", [["all"], ["ses-002_random-key"], ["all_non_ses"]]
    )
    @pytest.mark.parametrize(
        "datatype", [["all"], ["anat", "all_non_datatype"]]
    )
    def test_combinations_ssh_transfer(
        self,
        ssh_setup,
        sub_names,
        ses_names,
        datatype,
    ):
        """
        Test a subset of argument combinations while testing over SSH connection
        to a container. This is very slow, due to the rclone ssh transfer (which
        is performed twice in this test, once for upload, once for download), around
        8 seconds per parameterization.

        In test setup, the entire project is created in the `local_path` and
        is uploaded to `central_path`. So we only need to set up once per test,
        upload and download is to temporary folders and these temporary folders
        are cleaned at the end of each parameterization.
        """
        pathtable, project = ssh_setup

        # Upload data from the setup local project to a temporary
        # central directory.
        true_central_path = project.cfg["central_path"]
        tmp_central_path = (
            project.cfg["central_path"] / "tmp" / project.project_name
        )
        project.get_logging_path().mkdir(
            parents=True, exist_ok=True
        )  # TODO: why is this necessary

        project.update_config_file(central_path=tmp_central_path)

        project.upload_custom(
            "rawdata", sub_names, ses_names, datatype, init_log=False
        )

        expected_transferred_paths = self.get_expected_transferred_paths(
            pathtable, sub_names, ses_names, datatype
        )

        # Search the paths that were transferred and tidy them up,
        # then check against the paths that were expected to be transferred.
        transferred_files = ssh_test_utils.recursive_search_central(project)
        paths_to_transferred_files = self.remove_path_before_rawdata(
            transferred_files
        )

        assert sorted(paths_to_transferred_files) == sorted(
            expected_transferred_paths
        )

        # Now, move data from the central path where the project is
        # setup, to a temp local folder to test download.
        true_local_path = project.cfg["local_path"]
        tmp_local_path = (
            project.cfg["local_path"] / "tmp" / project.project_name
        )
        tmp_local_path.mkdir(exist_ok=True, parents=True)

        project.update_config_file(local_path=tmp_local_path)
        project.update_config_file(central_path=true_central_path)

        project.download_custom(
            "rawdata", sub_names, ses_names, datatype, init_log=False
        )

        # Find the transferred paths, tidy them up
        # and check expected paths were transferred.
        all_transferred = list((tmp_local_path / "rawdata").glob("**/*"))
        all_transferred = [
            path_ for path_ in all_transferred if path_.is_file()
        ]

        paths_to_transferred_files = self.remove_path_before_rawdata(
            all_transferred
        )

        assert sorted(paths_to_transferred_files) == sorted(
            expected_transferred_paths
        )

        # Clean up, removing the temp directories and
        # resetting the project paths.
        with paramiko.SSHClient() as client:
            ssh.connect_client_core(client, project.cfg)
            client.exec_command(f"rm -rf {(tmp_central_path).as_posix()}")

        shutil.rmtree(tmp_local_path)

        project.get_logging_path().mkdir(
            parents=True, exist_ok=True
        )  # TODO: why is this necessary
        project.update_config_file(local_path=true_local_path)
        project.get_logging_path().mkdir(
            parents=True, exist_ok=True
        )  # TODO: why is this necessary

    # ----------------------------------------------------------------------------------
    # Utils
    # ----------------------------------------------------------------------------------

    def get_expected_transferred_paths(
        self, pathtable, sub_names, ses_names, datatype
    ):
        """
        Process the expected files that are transferred using the logic in
        `make_pathtable_search_filter()` to
        """
        parsed_sub_names = self.parse_arguments(pathtable, sub_names, "sub")
        parsed_ses_names = self.parse_arguments(pathtable, ses_names, "ses")
        parsed_datatype = self.parse_arguments(pathtable, datatype, "datatype")

        # Filter pathtable to get files that were expected to be transferred
        (
            sub_ses_dtype_arguments,
            extra_arguments,
        ) = self.make_pathtable_search_filter(
            parsed_sub_names, parsed_ses_names, parsed_datatype
        )

        datatype_folders = self.query_table(pathtable, sub_ses_dtype_arguments)
        extra_folders = self.query_table(pathtable, extra_arguments)

        expected_paths = pd.concat([datatype_folders, extra_folders])
        expected_paths = expected_paths.drop_duplicates(subset="path")

        expected_paths = self.remove_path_before_rawdata(expected_paths.path)

        return expected_paths

    def make_pathtable_search_filter(self, sub_names, ses_names, datatype):
        """
        Create a string of arguments to pass to pd.query() that will
        create the table of only transferred sub, ses and datatype.

        Two arguments must be created, one of all sub / ses / datatypes
        and the other of all non sub/ non ses / non datatype
        folders. These must be handled separately as they are
        mutually exclusive.
        """
        sub_ses_dtype_arguments = []
        extra_arguments = []

        for sub in sub_names:
            if sub == "all_non_sub":
                extra_arguments += ["is_non_sub == True"]
            else:
                for ses in ses_names:
                    if ses == "all_non_ses":
                        extra_arguments += [
                            f"(parent_sub == '{sub}' & is_non_ses == True)"
                        ]
                    else:
                        for dtype in datatype:
                            if dtype == "all_non_datatype":
                                extra_arguments += [
                                    f"(parent_sub == '{sub}' & parent_ses == '{ses}' "
                                    f"& is_ses_level_non_datatype == True)"
                                ]
                            else:
                                sub_ses_dtype_arguments += [
                                    f"(parent_sub == '{sub}' & parent_ses == '{ses}' "
                                    f"& (parent_datatype == '{dtype}' "
                                    f"| parent_datatype == '{dtype}'))"
                                ]

        return sub_ses_dtype_arguments, extra_arguments

    def remove_path_before_rawdata(self, list_of_paths):
        """
        Remove the path to project files before the "rawdata" so
        they can be compared no matter where the project was stored
        (e.g. on a central server vs. local filesystem).
        """
        cut_paths = []
        for path_ in list_of_paths:
            parts = Path(path_).parts
            cut_paths.append(Path(*parts[parts.index("rawdata") :]))
        return cut_paths

    def query_table(self, pathtable, arguments):
        """
        Search the table for arguments, return empty
        if arguments empty
        """
        if any(arguments):
            folders = pathtable.query(" | ".join(arguments))
        else:
            folders = pd.DataFrame()
        return folders

    def parse_arguments(self, pathtable, list_of_names, field):
        """
        Replicate datashuttle name formatting by parsing
        "all" arguments and turning them into a list of all names,
        (subject or session), taken from the pathtable.
        """
        if list_of_names in [["all"], [f"all_{field}"]]:
            entries = pathtable.query(f"parent_{field} != False")[
                f"parent_{field}"
            ]
            entries = list(set(entries))
            if list_of_names == ["all"]:
                entries += (
                    [f"all_non_{field}"]
                    if field != "datatype"
                    else ["all_non_datatype"]
                )
            list_of_names = entries
        return list_of_names

    def create_all_pathtable_files(self, pathtable):
        """
        Create the entire test project in the defined
        location (usually project's `local_path`).
        """
        for i in range(pathtable.shape[0]):
            filepath = pathtable["base_folder"][i] / pathtable["path"][i]
            filepath.parents[0].mkdir(parents=True, exist_ok=True)
            test_utils.write_file(filepath, contents="test_entry")

    def central_from_local(self, path_):
        return Path(str(copy.copy(path_)).replace("local", "central"))
