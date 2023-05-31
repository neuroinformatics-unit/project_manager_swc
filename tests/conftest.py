import os
from pathlib import Path
from types import SimpleNamespace

import pytest
import test_utils
import yaml

from datashuttle.utils import utils


def get_canonical_test_dir_names(initialise=False):
    """
    SSH tests are run by copying data from a `local` project folder to a
    `remote` project folder through SSH. At present, the folder that is
    SSH too must also be accessible through the local filesystem (e.g. if
    SSH to a HPC, then the target directly must also be accessible through
    the local filesystem e.g. through a mounted drive).
    `test_data_filesystem_path` gives the local filesystem path to the folder,
    `test_data_server_path` gives the path after SSH connection to the folder.
    If SSH to `localhost`, both these paths will be the same.

    Returns
    -------

    save_ssh_key_project_name : Canonical project name used to store SSH key.
                                The test-project configs are deleted during
                                tear-down and so any pre-set SSH key pair must
                                be stored outside of this project.
                                `save_ssh_key_project_name` stores the project
                                name used internally for storing the SSH key
                                setup with `run_to_setup_ssh_test_key.py`
                                which is copied to the test-project configs
                                on test set up.

    test_data_filesystem_path : The path to the testing folder on the
                                filesystem where the `local` and `remote`
                                project folders be created during tests.
                                For SSH testing, this should be the local
                                filesystem path to the server path i.e. a
                                mounted drive. e.g.
                                W:/home/user/datashuttle_tests By default
                                (e.g. used for SSH tests to `localhost` this
                                is /home/.datashuttle_tests)

    test_data_server_path : Path to the testing folder once SSH connected to
                            the target server. For example
                            /home/user/datashuttle_tests. By default (e.g.
                            used for SSH tests to `localhost` this is
                            /home/.datashuttle_tests)

    ssh_key_path : Path to the SSH key setup by `run_to_setup_ssh_test_key.py`.
                   This is copied to the test-project during setup.

    config["test_ssh"] : bool indicating whether SSH tests should be run.

    config["username"] : Username for the account to connect with via SSH.

    config["remote_host_id"] : Target for SSH connection e.g. HPC address,
                               `localhost` for SSH to host machine. Note
                               sshing to `localhost` is only available on
                               macOS and linux.
    """
    # Load SSH setup configs
    config_filepath = (
        Path(os.path.dirname(os.path.realpath(__file__)))
        / "configs_for_ssh_tests.yaml"
    )

    with open(config_filepath) as file:
        config = yaml.full_load(file)

    # Check pre-setup SSH key-pair is set up
    save_ssh_key_project_name = "tests_ssh_key_holding_project"
    ssh_key_path = (
        utils.get_datashuttle_path(save_ssh_key_project_name)[0]
        / f"{save_ssh_key_project_name}_ssh_key"
    )

    if not initialise and config["test_ssh"] and not ssh_key_path.is_file():
        raise FileNotFoundError(
            f"Must run `run_to_setup_ssh_test_key` before running "
            f"SSH tests. {ssh_key_path}"
        )

    # Load filesystem and remote data paths
    if not config["test_data_filesystem_path"]:
        test_data_filesystem_path = Path.home() / ".datashuttle_tests"
    else:
        test_data_filesystem_path = config["test_data_filesystem_path"]

    if not config["test_data_server_path"]:
        test_data_server_path = Path.home() / ".datashuttle_tests"
    else:
        test_data_server_path = config["test_data_server_path"]

    return (
        save_ssh_key_project_name,
        test_data_filesystem_path,
        test_data_server_path,
        ssh_key_path,
        config["test_ssh"],
        config["username"],
        config["remote_host_id"],
    )


def pytest_configure(config):

    (
        __,
        test_data_filesystem_path,
        test_data_server_path,
        ssh_key_path,
        test_ssh,
        username,
        remote_host_id,
    ) = get_canonical_test_dir_names()

    pytest.ssh_config = SimpleNamespace(
        TEST_SSH=test_ssh,
        SSH_KEY_PATH=ssh_key_path,
        USERNAME=username,
        REMOTE_HOST_ID=remote_host_id,
        FILESYSTEM_PATH=str(test_data_filesystem_path),
        SERVER_PATH=str(test_data_server_path),
    )
    test_utils.set_datashuttle_loggers(disable=True)
