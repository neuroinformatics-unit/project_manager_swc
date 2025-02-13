""" """

import copy
import glob
import shutil
import time
from pathlib import Path

import pandas as pd
import pytest
import ssh_test_utils
import test_utils
from file_conflicts_pathtable import get_pathtable
from pytest import ssh_config


class TestFileTransfer:
    @pytest.fixture(
        scope="class",
        params=[  # Set running SSH or local filesystem (see docstring).
            # False,
            pytest.param(
                True,
                marks=pytest.mark.skipif(
                    ssh_config.TEST_SSH is False,
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

        For speed, create the project once,
        and all files to transfer. Then in the
        test function, the folder are transferred.
        Partial cleanup is done in the test function
        i.e. deleting the central_path to which the
        items have been transferred. This is achieved
        by using "class" scope.

        NOTES
        -----
        - Pytest params - The `params` key sets the
        `params` attribute on the pytest `request` fixture.
        This attribute is used to set the `testing_ssh` variable
        to `True` or `False`. In the first run, this is set to
        `False`, meaning local filesystem tests are run. In the
        second run, this is set with a pytest parameter that is
        `True` (i.e. SSH tests are run) but is skipped if `TEST_SSH`
        in `ssh_config` (set in conftest.py` is `False`.

        - For convenience, files are transferred
        with SSH and then checked through the local filesystem
        mount. This is significantly easier than checking
        everything through SFTP. However, on Windows the
        mounted filesystem is quite slow to update, taking
        a few seconds after SSH transfer. This makes the
        tests run very slowly. We can get rid
        of this limitation on linux.
        """
        testing_ssh = request.param
        tmp_path = tmpdir_factory.mktemp("test")

        if testing_ssh:
            base_path = ssh_config.FILESYSTEM_PATH
            central_path = ssh_config.SERVER_PATH
        else:
            base_path = tmp_path / "test with space"
            central_path = base_path
        test_project_name = "test_file_conflicts"

        project, cwd = test_utils.setup_project_fixture(
            base_path, test_project_name
        )

        if testing_ssh:
            ssh_test_utils.setup_project_for_ssh(
                project,
                test_utils.make_test_path(
                    central_path, "central", test_project_name
                ),
                ssh_config.CENTRAL_HOST_ID,
                ssh_config.USERNAME,
            )

            # Initialise the SSH connection
            ssh_test_utils.setup_hostkeys(project)
            shutil.copy(ssh_config.SSH_KEY_PATH, project.cfg.file_path.parent)

        pathtable = get_pathtable(project.cfg["local_path"])
        test_utils.create_all_pathtable_files(pathtable)
        project.testing_ssh = testing_ssh

        yield [pathtable, project]

        test_utils.teardown_project(cwd, project)

        if testing_ssh:
            for result in glob.glob(ssh_config.FILESYSTEM_PATH):
                shutil.rmtree(result)

    # -------------------------------------------------------------------------
    # Utils
    # -------------------------------------------------------------------------

    def central_from_local(self, path_):
        return Path(str(copy.copy(path_)).replace("local", "central"))

    # -------------------------------------------------------------------------
    # Test File Transfer - All Options
    # -------------------------------------------------------------------------

    @pytest.mark.parametrize(
        "sub_names",
        [
            ["all"],
            ["all_sub"],
            #         ["all_non_sub"],
            #         ["sub-001"],
            #         ["sub-003_date-20231901"],
            #         ["sub-002", "all_non_sub"],
        ],
    )
    @pytest.mark.parametrize(
        "ses_names",
        [
            ["all"],
            ["all_non_ses"],
            #       ["all_ses"],
            #       ["ses-001"],
            #       ["ses-002_random-key"],
            #       ["all_non_ses", "ses-001"],
        ],
    )
    @pytest.mark.parametrize(
        "datatype",
        [
            ["all"],
            ["all_non_datatype"],
            #        ["all_datatype"],
            #        ["behav"],
            #        ["ephys"],
            #        ["anat"],
            #       ["funcimg"],
            #        ["anat", "behav", "all_non_datatype"],
        ],
    )
    @pytest.mark.parametrize("upload_or_download", ["upload", "download"])
    def test_all_data_transfer_options(
        self,
        pathtable_and_project,
        sub_names,
        ses_names,
        datatype,
        upload_or_download,
    ):
        """
        Parse the arguments to filter the pathtable, getting
        the files expected to be transferred passed on the arguments
        Note files in sub/ses/datatype folders must be handled
        separately to those in non-sub, non-ses, non-datatype folders

        see test_utils.swap_local_and_central_paths() for the logic
        on setting up and swapping local / central paths for
        upload / download tests.
        """
        pathtable, project = pathtable_and_project

        transfer_function = test_utils.handle_upload_or_download(
            project,
            upload_or_download,
            transfer_method="custom",
            swap_last_folder_only=project.testing_ssh,
        )[0]

        transfer_function(
            "rawdata", sub_names, ses_names, datatype, init_log=False
        )

        if upload_or_download == "download":
            test_utils.swap_local_and_central_paths(
                project, swap_last_folder_only=project.testing_ssh
            )

        sub_names = self.parse_arguments(pathtable, sub_names, "sub")
        ses_names = self.parse_arguments(pathtable, ses_names, "ses")
        datatype = self.parse_arguments(pathtable, datatype, "datatype")

        # Filter pathtable to get files that were expected
        # to be transferred
        (
            sub_ses_dtype_arguments,
            extra_arguments,
        ) = self.make_pathtable_search_filter(sub_names, ses_names, datatype)

        datatype_folders = self.query_table(pathtable, sub_ses_dtype_arguments)
        extra_folders = self.query_table(pathtable, extra_arguments)

        expected_paths = pd.concat([datatype_folders, extra_folders])
        expected_paths = expected_paths.drop_duplicates(subset="path")

        central_base_paths = expected_paths.base_folder.map(
            lambda x: str(x).replace("local", "central")
        )
        expected_transferred_paths = central_base_paths / expected_paths.path

        # When transferring with SSH, there is a delay before
        # filesystem catches up
        if project.testing_ssh:
            time.sleep(0.5)

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

    # ---------------------------------------------------------------------------------------------------------------
    # Utils
    # ---------------------------------------------------------------------------------------------------------------

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
