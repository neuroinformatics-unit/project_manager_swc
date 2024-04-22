import shutil

import paramiko
import pytest
import ssh_test_utils
from base_transfer import BaseTransfer

# from pytest import ssh_config
from datashuttle.utils import ssh

TEST_SSH = ssh_test_utils.get_test_ssh()


@pytest.mark.skipif("not TEST_SSH", reason="TEST_SSH is false")
class TestSSHTransfer(BaseTransfer):

    @pytest.fixture(
        scope="class",
    )
    def ssh_setup(self, pathtable_and_project, setup_ssh_container):
        """
        After initial project setup (in `pathtable_and_project`)
        setup a container and the project's SSH connection to the container.
        Then upload the test project to the `central_path`.
        """
        pathtable, project = pathtable_and_project

        ssh_test_utils.setup_project_for_ssh(
            project,
            central_path=f"/home/sshuser/datashuttle/{project.project_name}",
            central_host_id="localhost",
            central_host_username="sshuser",
        )

        ssh_test_utils.setup_ssh_connection(project)

        project.upload_rawdata()

        return [pathtable, project]

    # -----------------------------------------------------------------
    # Test Setup SSH Connection
    # -----------------------------------------------------------------

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
        self.remake_logging_path(project)

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

        self.remake_logging_path(project)
        project.update_config_file(local_path=true_local_path)

    def remake_logging_path(self, project):
        """
        Need to do this to compensate for switching
        local_path location in the test environment.
        """
        project.get_logging_path().mkdir(parents=True, exist_ok=True)  # TOD
