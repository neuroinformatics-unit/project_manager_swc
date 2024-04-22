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

PORT = 3306  # https://github.com/orgs/community/discussions/25550
os.environ["DS_SSH_PORT"] = str(PORT)


def setup_project_for_ssh(
    project, central_path, central_host_id, central_host_username
):
    """
    Set up the project configs to use SSH connection
    to central
    """
    project.update_config_file(
        connection_method="ssh",
        central_path=central_path,
        central_host_id=central_host_id,
        central_host_username=central_host_username,
    )
    rclone.setup_rclone_config_for_ssh(
        project.cfg,
        project.cfg.get_rclone_config_name("ssh"),
        project.cfg.ssh_key_path,
    )


def setup_mock_input(input_):
    """
    This is very similar to pytest monkeypatch but
    using that was giving me very strange output,
    monkeypatch.setattr('builtins.input', lambda _: "n")
    i.e. pdb went deep into some unrelated code stack
    """
    orig_builtin = copy.deepcopy(builtins.input)
    builtins.input = lambda _: input_  # type: ignore
    return orig_builtin


def restore_mock_input(orig_builtin):
    """
    orig_builtin: the copied, original builtins.input
    """
    builtins.input = orig_builtin


def setup_ssh_connection(project, setup_ssh_key_pair=True):
    """
    Convenience function to verify the server hostkey.

    This requires monkeypatching a number of functions involved
    in the SSH setup process. `input()` is patched to always
    return the required hostkey confirmation "y". `getpass()` is
    patched to always return the password for the container in which
    SSH tests are run. `isatty()` is patched because when running this
    for some reason it appears to be in a TTY - this might be a
    container thing.
    """
    # Monkeypatch
    orig_builtin = setup_mock_input(input_="y")
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
    restore_mock_input(orig_builtin)
    ssh.getpass.getpass = orig_getpass
    sys.stdin.isatty = orig_isatty

    return verified


def setup_project_and_container_for_ssh(project):
    """"""
    assert docker_is_running(), (
        "docker is not running, "
        "this should be checked at the top of test script"
    )

    image_path = Path(__file__).parent / "ssh_test_images"
    os.chdir(image_path)

    if platform.system() == "Linux":
        build_command = "sudo docker build -t ssh_server ."
        run_command = f"sudo docker run -d -p {PORT}:22 ssh_server"
    else:
        build_command = "docker build ."
        run_command = f"docker run -d -p {PORT}:22 ssh_server"

    build_output = subprocess.run(
        build_command,
        shell=True,
        capture_output=True,
    )
    assert (
        build_output.returncode == 0
    ), f"docker build failed with: STDOUT-{build_output.stdout} STDERR-{build_output.stderr}"

    run_output = subprocess.run(
        run_command,
        shell=True,
        capture_output=True,
    )

    assert (
        run_output.returncode == 0
    ), f"docker run failed with: STDOUT-{run_output.stdout} STDERR-{run_output.stderr}"

    setup_project_for_ssh(
        project,
        central_path=f"/home/sshuser/datashuttle/{project.project_name}",
        central_host_id="localhost",
        central_host_username="sshuser",
    )


def sftp_recursive_file_search(sftp, path_, all_filenames):
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


def recursive_search_central(project):
    """ """
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


def get_test_ssh():
    """"""
    docker_installed = docker_is_running()
    if not docker_installed:
        warnings.warn(
            "SSH tests are not run as docker either not installed or running."
        )
    return docker_installed


def docker_is_running():
    """"""
    if not is_docker_installed():
        return False

    is_running = check_sys_command_returns_0("docker stats --no-stream")
    return is_running


def is_docker_installed():
    """"""
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
