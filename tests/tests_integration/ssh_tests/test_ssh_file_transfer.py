import copy
import glob
import shutil
from pathlib import Path

import pandas as pd
import pytest
import ssh_test_utils
import test_utils
from pytest import ssh_config
from test_file_conflicts_pathtable import get_pathtable


class TestFileTransfer:
    @pytest.fixture(
        scope="class",
        params=[
            False,
            pytest.param(
                True,
                marks=pytest.mark.skipif(
                    not ssh_config.TEST_SSH,
                    reason="TEST_SSH is set to False.",
                ),
            ),
        ],
    )
    def pathtable_and_project(self, request, tmpdir_factory):
        """
        Create a project for SSH testing. Setup
        the project as normal, and switch configs
        to use SSH connection.

        Although SSH is used for transfer, for SSH tests,
        checking the created filepaths is always
        done through the local filesystem for speed
        and convenience. As such, the drive that is
        SSH to must also be mounted and the path
        supplied to the location SSH'd to.

        For speed, create the project once (including
        all files to transfer) once. This is achieved
        by using "class" scope.
        """
        testing_ssh = request.param
        tmp_path = tmpdir_factory.mktemp("test")
        test_project_name = "test_file_conflicts"

        if testing_ssh:
            base_path = ssh_config.FILESYSTEM_PATH
            remote_path = ssh_config.SERVER_PATH
        else:
            base_path = tmp_path / "test with space"
            remote_path = base_path

        project, cwd = test_utils.setup_project_fixture(
            base_path, test_project_name
        )

        if testing_ssh:
            ssh_test_utils.setup_project_for_ssh(
                project,
                test_utils.make_test_path(
                    remote_path, test_project_name, "remote"
                ),
                ssh_config,
            )

        pathtable = get_pathtable(project.cfg["local_path"])
        self.create_all_pathtable_files(pathtable)
        project.testing_ssh = testing_ssh

        yield [pathtable, project]

        test_utils.teardown_project(cwd, project)

        if testing_ssh:
            for result in glob.glob(ssh_config.FILESYSTEM_PATH):
                shutil.rmtree(result)

    # -------------------------------------------------------------------------
    # Utils
    # -------------------------------------------------------------------------

    def remote_from_local(self, path_):
        return Path(str(copy.copy(path_)).replace("local", "remote"))

    # -------------------------------------------------------------------------
    # Test File Transfer - All Options
    # -------------------------------------------------------------------------

    @pytest.mark.parametrize(
        "sub_names",
        [
            ["all"],
            ["all_sub"],
            ["all_non_sub"],
            ["sub-001"],
            ["sub-003_date-20231901"],
            ["sub-002", "all_non_sub"],
        ],
    )
    @pytest.mark.parametrize(
        "ses_names",
        [
            ["all"],
            ["all_non_ses"],
            ["all_ses"],
            ["ses-001"],
            ["ses-002_random-key"],
            ["all_non_ses", "ses-001"],
        ],
    )
    @pytest.mark.parametrize(
        "data_type",
        [
            ["all"],
            ["all_ses_level_non_data_type"],
            ["all_data_type"],
            ["behav"],
            ["ephys"],
            ["histology"],
            ["funcimg"],
            ["histology", "behav", "all_ses_level_non_data_type"],
        ],
    )
    @pytest.mark.parametrize("upload_or_download", ["upload", "download"])
    def test_all_data_transfer_options(
        self,
        pathtable_and_project,
        sub_names,
        ses_names,
        data_type,
        upload_or_download,
    ):
        """
        Parse the arguments to filter the pathtable, getting
        the files expected to be transferred pased on the arguments
        Note files in sub/ses/datatype folders must be handled
        separately to those in non-sub, non-ses, non-data-type folders

        see test_utils.swap_local_and_remote_paths() for the logic
        on setting up and swapping local / remote paths for
        upload / download tests.
        """
        pathtable, project = pathtable_and_project

        transfer_function = test_utils.handle_upload_or_download(
            project,
            upload_or_download,
            swap_last_folder_only=project.testing_ssh,
        )[0]

        transfer_function(sub_names, ses_names, data_type, init_log=False)

        if upload_or_download == "download":
            test_utils.swap_local_and_remote_paths(
                project, swap_last_folder_only=project.testing_ssh
            )

        sub_names = self.parse_arguments(pathtable, sub_names, "sub")
        ses_names = self.parse_arguments(pathtable, ses_names, "ses")
        data_type = self.parse_arguments(pathtable, data_type, "data_type")

        # Filter pathtable to get files that were expected
        # to be transferred
        (
            sub_ses_dtype_arguments,
            extra_arguments,
        ) = self.make_pathtable_search_filter(sub_names, ses_names, data_type)

        data_type_folders = self.query_table(
            pathtable, sub_ses_dtype_arguments
        )
        extra_folders = self.query_table(pathtable, extra_arguments)

        expected_paths = pd.concat([data_type_folders, extra_folders])
        expected_paths = expected_paths.drop_duplicates(subset="path")

        remote_base_paths = expected_paths.base_folder.map(
            lambda x: str(x).replace("local", "remote")
        )
        expected_transferred_paths = remote_base_paths / expected_paths.path

        # Check what paths were actually moved
        # (through the local filesystem), and test
        path_to_search = (
            self.remote_from_local(project.cfg["local_path"]) / "rawdata"
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
            shutil.rmtree(self.remote_from_local(project.cfg["local_path"]))
        except FileNotFoundError:
            pass

    # -------------------------------------------------------------------------
    # Utils
    # -------------------------------------------------------------------------

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
                    if field != "data_type"
                    else ["all_ses_level_non_data_type"]
                )
            list_of_names = entries
        return list_of_names

    def create_all_pathtable_files(self, pathtable):
        """ """
        for i in range(pathtable.shape[0]):
            filepath = pathtable["base_folder"][i] / pathtable["path"][i]
            filepath.parents[0].mkdir(parents=True, exist_ok=True)
            test_utils.write_file(filepath, contents="test_entry")

    def make_pathtable_search_filter(self, sub_names, ses_names, data_type):
        """
        Create a string of arguments to pass to pd.query() that will
        create the table of only transferred sub, ses and data_type.

        Two arguments must be created, one of all sub / ses / datatypes
        and the other of all non sub/ non ses / non data type
        folders. These must be handled separately as they are
        mutually exclusive.
        """
        sub_ses_dtype_arguments = []
        extra_arguments = []

        for sub in sub_names:

            if sub == "all_non_sub":
                extra_arguments += ["is_non_sub == True"]
            else:
                if "histology" in data_type:
                    sub_ses_dtype_arguments += [
                        f"(parent_sub == '{sub}' & "
                        f"(parent_data_type == 'histology' | "
                        f"parent_data_type == 'histology'))"
                    ]

                for ses in ses_names:

                    if ses == "all_non_ses":
                        extra_arguments += [
                            f"(parent_sub == '{sub}' & is_non_ses == True)"
                        ]
                    else:

                        for dtype in data_type:
                            if dtype == "all_ses_level_non_data_type":
                                extra_arguments += [
                                    f"(parent_sub == '{sub}' & "
                                    f"parent_ses == '{ses}' & "
                                    f"is_ses_level_non_data_type == True)"
                                ]
                            else:
                                sub_ses_dtype_arguments += [
                                    f"(parent_sub == '{sub}' & "
                                    f"parent_ses == '{ses}' & "
                                    f"(parent_data_type == '{dtype}' | "
                                    f"parent_data_type == '{dtype}'))"
                                ]

        return sub_ses_dtype_arguments, extra_arguments
