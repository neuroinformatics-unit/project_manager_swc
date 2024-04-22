"""

"""

import builtins
import copy
import os
import platform
import stat
import subprocess
import sys
import warnings
from pathlib import Path

import paramiko

from datashuttle.utils import rclone, ssh

# Choose port 3306 for running on GH actions
# suggested in https://github.com/orgs/community/discussions/25550
PORT = 3306
os.environ["DS_SSH_PORT"] = str(PORT)


def setup_project_for_ssh(
    project,
):
    """
    Set up the project configs to use
    SSH connection to central. The settings
    set up a connection to the Dockerfile image
    found in /ssh_test_images.
    """
    project.update_config_file(
        connection_method="ssh",
        central_path=f"/home/sshuser/datashuttle/{project.project_name}",
        central_host_id="localhost",
        central_host_username="sshuser",
    )
    rclone.setup_rclone_config_for_ssh(
        project.cfg,
        project.cfg.get_rclone_config_name("ssh"),
        project.cfg.ssh_key_path,
    )


def setup_ssh_connection(project, setup_ssh_key_pair=True):
    """
    Convenience function to verify the server hostkey and ssh
    key pairs to the Dockerfile image for ssh tests.

    This requires monkeypatching a number of functions involved
    in the SSH setup process. `input()` is patched to always
    return the required hostkey confirmation "y". `getpass()` is
    patched to always return the password for the container in which
    SSH tests are run. `isatty()` is patched because when running this
    for some reason it appears to be in a TTY - this might be a
    container thing.
    """
    # Monkeypatch
    orig_builtin = copy.deepcopy(builtins.input)
    builtins.input = lambda _: "y"  # type: ignore

    orig_getpass = copy.deepcopy(ssh.getpass.getpass)
    ssh.getpass.getpass = lambda _: "password"  # type: ignore

    orig_isatty = copy.deepcopy(sys.stdin.isatty)
    sys.stdin.isatty = lambda: True

    # Run setup
    verified = ssh.verify_ssh_central_host(
        project.cfg["central_host_id"], project.cfg.hostkeys_path, log=True
    )

    if setup_ssh_key_pair:
        ssh.setup_ssh_key(project.cfg, log=False)

    # Restore functions
    builtins.input = orig_builtin
    ssh.getpass.getpass = orig_getpass
    sys.stdin.isatty = orig_isatty

    return verified


def setup_ssh_container(container_name):
    """
    Build and run the docker container used for
    ssh tests.
    """
    assert docker_is_running(), (
        "docker is not running, "
        "this should be checked at the top of test script"
    )

    image_path = Path(__file__).parent / "ssh_test_images"
    os.chdir(image_path)

    if platform.system() != "Windows":
        build_command = "sudo docker build -t ssh_server ."
        run_command = (
            f"sudo docker run -d -p {PORT}:22 "
            f"--name {container_name} ssh_server"
        )
    else:
        build_command = "docker build ."
        run_command = (
            f"docker run -d -p {PORT}:22 --name {container_name}  ssh_server"
        )

    build_output = subprocess.run(
        build_command,
        shell=True,
        capture_output=True,
    )
    assert build_output.returncode == 0, (
        f"docker build failed with: STDOUT-{build_output.stdout} "
        f"STDERR-{build_output.stderr}"
    )

    run_output = subprocess.run(
        run_command,
        shell=True,
        capture_output=True,
    )

    assert run_output.returncode == 0, (
        f"docker run failed with: STDOUT-{run_output.stdout} "
        f"STDERR-{run_output.stderr}"
    )


def recursive_search_central(project):
    """
    A convenience function to recursively search a
    project for files through SSH, used  during testing
    across an SSH connection to collected names of
    files that were transferred.
    """
    with paramiko.SSHClient() as client:
        ssh.connect_client_core(client, project.cfg)

        sftp = client.open_sftp()

        all_filenames = []

        sftp_recursive_file_search(
            sftp,
            (project.cfg["central_path"] / "rawdata").as_posix(),
            all_filenames,
        )
    return all_filenames


def sftp_recursive_file_search(sftp, path_, all_filenames):
    """
    Append all filenames found within a folder,
    when searching over a sftp connection.
    """
    try:
        sftp.stat(path_)
    except FileNotFoundError:
        return

    for file_or_folder in sftp.listdir_attr(path_):
        if stat.S_ISDIR(file_or_folder.st_mode):
            sftp_recursive_file_search(
                sftp,
                path_ + "/" + file_or_folder.filename,
                all_filenames,
            )
        else:
            all_filenames.append(path_ + "/" + file_or_folder.filename)


def get_test_ssh():
    """
    Return bool indicating whether Docker is installed and running,
    which is required for ssh tests.
    """
    docker_installed = docker_is_running()
    if not docker_installed:
        warnings.warn(
            "SSH tests are not run as docker either not installed or running."
        )
    return docker_installed


def docker_is_running():
    if not is_docker_installed():
        return False

    is_running = check_sys_command_returns_0("docker stats --no-stream")
    return is_running


def is_docker_installed():
    return check_sys_command_returns_0("docker -v")


def check_sys_command_returns_0(command):
    return (
        subprocess.run(
            command,
            shell=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        ).returncode
        == 0
    )
