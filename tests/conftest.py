"""
Test configs, used for setting up SSH tests.

Before running these tests, it is necessary to setup
an SSH key. This can be done through datashuttle
ssh.setup_ssh_key(project.cfg, log=False).

Store this path somewhere outside of the test environment,
and it will be copied to the project test folder before testing.

FILESYSTEM_PATH and SERVER_PATH these must point
to the same folder on the HPC, filesystem,
as a mounted drive and server as the linux path to
connect through SSH
"""

import platform
from types import SimpleNamespace

import pytest
import test_utils

test_ssh = True
username = "jziminski"
central_host_id = "ssh.swc.ucl.ac.uk"
server_path = r"/ceph/neuroinformatics/neuroinformatics/scratch/datashuttle_tests/fake_data"


if platform.system() == "Windows":
    ssh_key_path = r"C:\Users\Joe\.datashuttle\test_file_conflicts_ssh_key"
    filesystem_path = "X:/neuroinformatics/scratch/datashuttle_tests/fake_data"

else:
    ssh_key_path = "/home/joe/test_file_conflicts_ssh_key"
    filesystem_path = "/home/joe/ceph_mount/neuroinformatics/scratch/datashuttle_tests/fake_data"


def pytest_configure(config):
    pytest.ssh_config = SimpleNamespace(
        TEST_SSH=test_ssh,
        SSH_KEY_PATH=ssh_key_path,
        USERNAME=username,
        CENTRAL_HOST_ID=central_host_id,
        FILESYSTEM_PATH=filesystem_path,  # FILESYSTEM_PATH and SERVER_PATH these must point to the same folder on the HPC, filesystem
        SERVER_PATH=server_path,  # as a mounted drive and server as the linux path to connect through SSH
    )
    test_utils.set_datashuttle_loggers(disable=True)
