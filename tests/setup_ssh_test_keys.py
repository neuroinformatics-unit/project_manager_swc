"""
This script will setup an SSH key pair between the SSH target
specified in `setup_configs_for_ssh_tests.yaml`. This will require
one-time password entry.

The SSH key pair is saved to a holding datashuttle project
specified in `conftest.py`. During setup of an SSH test project,
this SSH key pair is copied from the holding datashuttle
project to the SSH test-project. This means that when the test
project is deleted during tear-down, the SSH key is still available
for future testing
"""
import conftest

from datashuttle.datashuttle import DataShuttle

(
    save_ssh_key_project_name,
    test_data_filesystem_path,
    test_data_server_path,
    ssh_key_path,
    __,
    username,
    remote_host_id,
) = conftest.get_canonical_test_dir_names(initialise=True)

project = DataShuttle(save_ssh_key_project_name)

project.make_config_file(
    test_data_filesystem_path / "local",
    test_data_server_path / "remote",
    "ssh",
    remote_host_id=remote_host_id,
    remote_host_username=username,
    use_behav=True,
)

project.setup_ssh_connection_to_remote_server()
