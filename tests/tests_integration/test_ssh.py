import shutil
import subprocess

import paramiko
import pytest
import ssh_test_utils
import test_utils
from base_transfer import BaseTransfer

# from pytest import ssh_config
from datashuttle.utils import ssh

TEST_SSH = ssh_test_utils.get_test_ssh()


@pytest.mark.skipif("not TEST_SSH", reason="TEST_SSH is false")
class TestSSH(BaseTransfer):

    @pytest.fixture(
        scope="session",
    )
    def setup_ssh_container(self):
        # Annoying session scope does not seem to actually work
        container_name = "running_ssh_tests"
        ssh_test_utils.setup_ssh_container(container_name)
        yield
        subprocess.run(f"docker stop {container_name}", shell=True)
        subprocess.run(f"docker rm {container_name}", shell=True)

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

    @pytest.fixture(scope="function")
    def project(test, tmp_path, setup_ssh_container):
        """
        Make a project as per usual, but now add
        in test ssh configurations
        """
        tmp_path = tmp_path / "test with space"

        test_project_name = "test_ssh"
        project, cwd = test_utils.setup_project_fixture(
            tmp_path, test_project_name
        )
        ssh_test_utils.setup_project_for_ssh(
            project,
            central_path=f"/home/sshuser/datashuttle/{project.project_name}",
            central_host_id="localhost",
            central_host_username="sshuser",
        )
        yield project
        test_utils.teardown_project(cwd, project)

    # -----------------------------------------------------------------
    # Test Setup SSH Connection
    # -----------------------------------------------------------------

    @pytest.mark.parametrize("input_", ["n", "o", "@"])
    def test_verify_ssh_central_host_do_not_accept(
        self, capsys, project, input_
    ):
        """
        Use the main function to test this. Test the sub-function
        when accepting, because this main function will also
        call setup ssh key pairs which we don't want to do yet

        This should only accept for "y" so try some random strings
        including "n" and check they all do not make the connection.
        """
        orig_builtin = ssh_test_utils.setup_mock_input(input_)

        project.setup_ssh_connection()

        ssh_test_utils.restore_mock_input(orig_builtin)

        captured = capsys.readouterr()

        assert "Host not accepted. No connection made.\n" in captured.out

    def test_verify_ssh_central_host_accept(self, capsys, project):
        """
        User is asked to accept the server hostkey. Mock this here
        and check hostkey is successfully accepted and written to configs.
        """
        test_utils.clear_capsys(capsys)

        verified = ssh_test_utils.setup_ssh_connection(
            project, setup_ssh_key_pair=False
        )

        assert verified
        captured = capsys.readouterr()

        assert captured.out == "Host accepted.\n"

        with open(project.cfg.hostkeys_path, "r") as file:
            hostkey = file.readlines()[0]

        assert (
            f"[{project.cfg['central_host_id']}]:3306 ssh-ed25519 " in hostkey
        )

    def test_generate_and_write_ssh_key(self, project):
        """
        Check ssh key for passwordless connection is written
        to file
        """
        path_to_save = project.cfg["local_path"] / "test"
        ssh.generate_and_write_ssh_key(path_to_save)

        with open(path_to_save, "r") as file:
            first_line = file.readlines()[0]

        assert first_line == "-----BEGIN RSA PRIVATE KEY-----\n"

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
