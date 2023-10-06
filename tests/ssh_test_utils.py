import builtins
import copy

from datashuttle.utils import rclone, ssh


def setup_project_for_ssh(
    project, central_path, central_host_id, central_host_username
):
    """
    Set up the project configs to use SSH connection
    to central
    """
    project.update_config_file(
        central_path=central_path,
    )
    project.update_config_file(central_host_id=central_host_id)
    project.update_config_file(central_host_username=central_host_username)
    project.update_config_file(connection_method="ssh")

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


def setup_hostkeys(project):
    """
    Convenience function to verify the server hostkey.
    """
    orig_builtin = setup_mock_input(input_="y")
    ssh.verify_ssh_central_host(
        project.cfg["central_host_id"], project.cfg.hostkeys_path, log=True
    )
    restore_mock_input(orig_builtin)

    orig_getpass = copy.deepcopy(ssh.getpass.getpass)
    ssh.getpass.getpass = lambda _: "password"

    ssh.setup_ssh_key(project.cfg, log=False)
    ssh.getpass.getpass = orig_getpass


def build_docker_image(project):
    import os
    import subprocess
    from pathlib import Path

    image_path = Path(__file__).parent / "ssh_test_images"
    os.chdir(image_path)
    subprocess.run("docker build -t ssh_server .", shell=True)
    subprocess.run(
        "docker run -d -p 22:22 ssh_server", shell=True
    )  # ; docker build -t ssh_server .", shell=True)  # ;docker run -p 22:22 ssh_server

    setup_project_for_ssh(
        project,
        central_path=f"/home/sshuser/datashuttle/{project.project_name}",
        central_host_id="localhost",
        central_host_username="sshuser",
    )
