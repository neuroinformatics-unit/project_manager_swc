import builtins
import copy
import shutil

from datashuttle.utils import rclone, ssh


def setup_project_for_ssh(
    project, remote_path, ssh_config, setup_ssh_connection=True
):
    """
    Setup the project configs to use SSH connection
    to remote
    """
    project.update_config(
        "remote_path",
        remote_path,
    )
    project.update_config("remote_host_id", ssh_config.REMOTE_HOST_ID)
    project.update_config("remote_host_username", ssh_config.USERNAME)
    project.update_config("connection_method", "ssh")

    if setup_ssh_connection:
        setup_hostkeys(project)

        shutil.copy(ssh_config.SSH_KEY_PATH, project.cfg.ssh_key_path)

        rclone.setup_remote_as_rclone_target(
            "ssh",
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
    ssh.verify_ssh_remote_host(
        project.cfg["remote_host_id"], project.cfg.hostkeys_path, log=True
    )
    restore_mock_input(orig_builtin)
