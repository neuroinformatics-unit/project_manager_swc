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
from file_conflicts_pathtable import get_pathtable
#from pytest import ssh_config

from datashuttle.utils import ssh

TEST_SSH = True  # TODO: base on whether docker / singularity is installed.


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


class TestFileTransfer:
    @pytest.fixture(
        scope="class",
    )
    def pathtable_and_project(self, tmpdir_factory):
        """ """
        tmp_path = tmpdir_factory.mktemp("test")

        base_path = tmp_path / "test with space"
        test_project_name = "test_file_conflicts"

        project, cwd = test_utils.setup_project_fixture(
            base_path, test_project_name
        )

        pathtable = get_pathtable(project.cfg["local_path"])

        self.create_all_pathtable_files(pathtable)

        yield [pathtable, project]

        test_utils.teardown_project(cwd, project)

    @pytest.fixture(
        scope="class",
    )
    def ssh_setup(self, pathtable_and_project):
        pathtable, project = pathtable_and_project
        ssh_test_utils.build_docker_image(project)
        ssh_test_utils.setup_hostkeys(project)

        project.upload_all()

        return [pathtable, project]

    # -------------------------------------------------------------------------
    # Utils
    # -------------------------------------------------------------------------

    def central_from_local(self, path_):
        return Path(str(copy.copy(path_)).replace("local", "central"))

    # -------------------------------------------------------------------------
    # Test File Transfer - All Options
    # -------------------------------------------------------------------------

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
        """ """
        pathtable, project = pathtable_and_project

        transfer_function = test_utils.handle_upload_or_download(
            project,
            upload_or_download,
            transfer_method="custom",
            swap_last_folder_only=False,
        )[0]

        transfer_function("rawdata", sub_names, ses_names, datatype, init_log=False)

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

        assert sorted(paths_to_transferred_files) == sorted(
            expected_transferred_paths
        )

        # Teardown here, because we have session scope.
        try:
            shutil.rmtree(self.central_from_local(project.cfg["local_path"]))
        except FileNotFoundError:
            pass

    @pytest.mark.parametrize("sub_names", PARAM_SUBS)
    @pytest.mark.parametrize("ses_names", PARAM_SES)
    @pytest.mark.parametrize("datatype", PARAM_DATATYPE)
    def test_combinations_ssh_transfer(
        self,
        ssh_setup,
        sub_names,
        ses_names,
        datatype,
    ):
        """ """
        pathtable, project = ssh_setup

        true_central_path = project.cfg["central_path"]
        tmp_central_path = project.cfg["central_path"] / "tmp"
        project.update_config("central_path", tmp_central_path)

        breakpoint()
        project.upload(sub_names, ses_names, datatype, init_log=False)

        expected_transferred_paths = self.get_expected_transferred_paths(
            pathtable, sub_names, ses_names, datatype
        )

        transferred_files = ssh_test_utils.recursive_search_central(project)

        paths_to_transferred_files = self.remove_path_before_rawdata(
            transferred_files
        )

        expected_transferred_paths_ = self.remove_path_before_rawdata(
            expected_transferred_paths
        )

        assert sorted(paths_to_transferred_files) == sorted(
            expected_transferred_paths_
        )

        with paramiko.SSHClient() as client:
            ssh.connect_client(client, project.cfg)
            client.exec_command(
                f"rm -rf {(tmp_central_path).as_posix()}"
            )  # TODO: own function as need to do on teardown)

        true_local_path = project.cfg["local_path"]
        tmp_local_path = project.cfg["local_path"] / "tmp"
        tmp_local_path.mkdir()
        project.update_config("local_path", tmp_local_path)
        project.update_config("central_path", true_central_path)

        project.download(
            sub_names, ses_names, datatype, init_log=False
        )  # TODO: why is this connecting so many times? [during search - make issue]

        all_transferred = list((tmp_local_path / "rawdata").glob("**/*"))
        all_transferred = [
            path_ for path_ in all_transferred if path_.is_file()
        ]

        paths_to_transferred_files = self.remove_path_before_rawdata(
            all_transferred
        )

        assert sorted(paths_to_transferred_files) == sorted(
            expected_transferred_paths_
        )

        shutil.rmtree(tmp_local_path)
        project.update_config("local_path", true_local_path)

    # ---------------------------------------------------------------------------------------------------------------
    # Utils
    # ---------------------------------------------------------------------------------------------------------------

    def get_expected_transferred_paths(
        self, pathtable, sub_names, ses_names, datatype
    ):
        """"""
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

        central_base_paths = expected_paths.base_folder.map(
            lambda x: str(x).replace("local", "central")
        )
        expected_transferred_paths = central_base_paths / expected_paths.path

        return expected_transferred_paths

    def remove_path_before_rawdata(self, list_of_paths):
        cut_paths = []
        for path_ in list_of_paths:  # TODO: rename all filenames
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
                                    f"(parent_sub == '{sub}' & parent_ses == '{ses}' & is_ses_level_non_datatype == True)"
                                ]
                            else:
                                sub_ses_dtype_arguments += [
                                    f"(parent_sub == '{sub}' & parent_ses == '{ses}' & (parent_datatype == '{dtype}' | parent_datatype == '{dtype}'))"
                                ]

        return sub_ses_dtype_arguments, extra_arguments
