import shutil

import pytest
import test_utils
from base import BaseTest

from datashuttle import DataShuttle
from datashuttle.utils.custom_exceptions import (
    ConfigError,
)

TEST_PROJECT_NAME = "test_project"


class TestLocalOnlyProject(BaseTest):

    def test_bad_setup(self, tmp_path):
        """
        Test setup without providing both central_path and connection
        method (distinguishing a full vs local-only project)
        """
        local_path = tmp_path / "test_local"

        project = DataShuttle("this_project_is_not_torn_down")

        with pytest.raises(ConfigError) as e:
            project.make_config_file(
                local_path, central_path=tmp_path / "central"
            )
        assert (
            "Either both `central_path` and `connection_method` must be set"
            in str(e.value)
        )

        with pytest.raises(ConfigError) as e:
            project.make_config_file(local_path, connection_method="ssh")
        assert (
            "Either both `central_path` and `connection_method` must be set"
            in str(e.value)
        )

    @pytest.mark.parametrize("project", ["local"], indirect=True)
    def test_full_to_local_project(self, project):
        """
        Make a full project a local-only project, and check the transfer
        functionality is now restricted.
        """
        project.update_config_file(central_path=None, connection_method=None)

        with pytest.raises(ConfigError) as e:
            project.upload_entire_project()

        assert "This function cannot be used for a local-project." in str(
            e.value
        )

        project.create_folders("rawdata", "sub-001", "ses-001", "ephys")

        project.validate_project("rawdata", "error")

    @pytest.mark.parametrize("project", ["local"], indirect=True)
    def test_local_project_to_full(self, tmp_path, project):
        """
        Test updating a local-only project to a full one
        by adding the required configs (both must be set together)
        Perform a quick check that data transfer does not error out
        now that the project is full, and the configs are set as expected.
        """
        central_path = tmp_path / "central"
        connection_method = "local_filesystem"

        # check must set both at once
        with pytest.raises(ConfigError):
            project.update_config_file(central_path=central_path)

        with pytest.raises(ConfigError):
            project.update_config_file(connection_method=connection_method)

        project.update_config_file(
            central_path=central_path, connection_method=connection_method
        )

        # smoke test, should not raise now is a full project.
        project.upload_entire_project()

        assert project.cfg["central_path"] == central_path / TEST_PROJECT_NAME
        assert project.cfg["connection_method"] == connection_method

    @pytest.mark.parametrize("project", ["local"], indirect=True)
    def test_local_to_full_project(self, project):
        """
        Change a project from local-only to a normal project by updating
        the relevant configs. Smoke test that general functionality is maintained
        and that transfers work correctly.
        """
        central_path = project.cfg["local_path"].parent / "central"

        project.update_config_file(
            central_path=central_path, connection_method="local_filesystem"
        )

        paths_ = project.create_folders(
            "rawdata", "sub-001", "ses-001", "ephys"
        )
        test_utils.write_file(
            paths_["ephys"][0] / "test_file", contents="test_entry"
        )

        project.validate_project("rawdata", "error")

        project.upload_entire_project()

        assert (
            central_path
            / TEST_PROJECT_NAME
            / "rawdata"
            / "sub-001"
            / "ses-001"
            / "ephys"
            / "test_file"
        ).is_file()

    @pytest.mark.parametrize("top_level_folder", ["rawdata", "derivatives"])
    @pytest.mark.parametrize("project", ["full"], indirect=True)
    def test_get_next_sub_and_ses(self, project, top_level_folder):
        """
        Make a 'full' project with subject and session > 1 in both local
        and central projects. Then, delete the local and run get next sub / ses,
        and make the project local-only. Call validation requesting to also
        check central path, which should be ignored as we are in local-only mode.
        """
        test_utils.make_local_folders_with_files_in(
            project,
            top_level_folder,
            subs=["001", "002", "003"],
            sessions=["01", "02"],
        )

        project.upload_entire_project()

        shutil.rmtree(project.cfg["local_path"] / top_level_folder)

        project.update_config_file(central_path=None, connection_method=None)

        next_sub = project.get_next_sub(top_level_folder, local_only=True)

        next_ses = project.get_next_ses(
            top_level_folder, local_only=True, sub="001"
        )

        assert next_sub == "sub-001"
        assert next_ses == "ses-001"
