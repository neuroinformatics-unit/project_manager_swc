import os

import pytest
import test_utils
from base import BaseTest

from datashuttle import DataShuttle
from datashuttle.utils import getters
from datashuttle.utils.custom_exceptions import ConfigError


class TestConfigs(BaseTest):
    # Test Errors
    # -------------------------------------------------------------

    @pytest.fixture(scope="function")
    def non_existent_path(self, tmp_path):
        """
        Return a path that does not exist.
        """
        non_existent_path = tmp_path / "does_not_exist"
        assert not non_existent_path.is_dir()
        return non_existent_path

    @pytest.fixture(scope="function")
    def existent_path(self, tmp_path):
        """
        Return a path that exists.
        """
        existent_path = tmp_path / "exists"
        os.makedirs(existent_path, exist_ok=True)
        return existent_path

    def test_warning_on_startup(self, no_cfg_project):
        """
        When no configs have been set, a warning should be shown that
        the config has not been initialized. Need to download
        Rclone first to ensure input() is not called.
        """
        project_name = no_cfg_project.project_name
        test_utils.delete_project_if_it_exists(project_name)

        with pytest.warns() as w:
            DataShuttle(project_name)

        assert len(w) == 1
        assert (
            str(w[0].message)
            == "Configuration file has not been initialized. "
            "Use make_config_file() to setup before continuing."
        )

    @pytest.mark.parametrize(
        "bad_pattern",
        [
            "~/my/path",
            ".",
            "../my/path",
        ],
    )
    @pytest.mark.parametrize("path_type", ["local_path", "central_path"])
    def test_bad_path_syntax(self, project, bad_pattern, path_type, tmp_path):
        """
        "~", "." and "../" syntax is not supported because
        it does not work with rclone. Theoretically it
        could be supported by checking for "." etc. and
        filling in manually, but it does not seem robust.

        Here check an error is raised when path contains
        incorrect syntax.

        Note pathlib strips "./" so not checked.
        """
        if bad_pattern != ".":
            bad_pattern = f"{bad_pattern}/{project.project_name}"
        good_pattern = f"{tmp_path}/my/path/{project.project_name}"

        if path_type == "local_path":
            local_path = bad_pattern
            central_path = good_pattern
        else:
            local_path = good_pattern
            central_path = bad_pattern

        os.makedirs(local_path, exist_ok=True)
        os.makedirs(central_path, exist_ok=True)

        with pytest.raises(ConfigError) as e:
            project.update_config_file(
                local_path=local_path,
                central_path=central_path,
                connection_method="local_filesystem",
            )

        assert "must contain the full folder path with no " in str(e.value)

    def test_no_ssh_options_set_on_make_config_file(self, no_cfg_project):
        """
        Check that program will assert if not all ssh options
        are set on make_config_file
        """
        with pytest.raises(ConfigError) as e:
            no_cfg_project.make_config_file(
                no_cfg_project.project_name,
                no_cfg_project.project_name,
                "ssh",
            )

        assert (
            str(e.value)
            == "'central_host_id' and 'central_host_username' are "
            "required if 'connection_method' is 'ssh'."
        )

    # Test Make Configs API
    # -------------------------------------------------------------

    def test_required_configs(self, no_cfg_project, tmp_path):
        """
        Set the required arguments of the config (local_path, central_path,
        connection_method and check they are set correctly in both
        the no_cfg_project.cfg dict and config.yaml file.
        """
        required_options = test_utils.get_test_config_arguments_dict(
            tmp_path, no_cfg_project.project_name, required_arguments_only=True
        )

        no_cfg_project.make_config_file(**required_options)

        self.check_config_reopen_and_check_config_again(
            no_cfg_project,
            required_options,
        )

    def test_config_defaults(self, no_cfg_project, tmp_path):
        """
        Check the default configs are set as expected
        (see get_test_config_arguments_dict()) for tested defaults.
        """
        required_options = test_utils.get_test_config_arguments_dict(
            tmp_path, no_cfg_project.project_name, required_arguments_only=True
        )

        no_cfg_project.make_config_file(**required_options)

        default_options = test_utils.get_test_config_arguments_dict(
            tmp_path, no_cfg_project.project_name, set_as_defaults=True
        )

        test_utils.check_configs(no_cfg_project, default_options)

    def test_non_default_configs(self, no_cfg_project, tmp_path):
        """
        Set the configs to non-default options, make the
        config file and check file and no_cfg_project.cfg are set correctly.
        """
        changed_configs = test_utils.get_test_config_arguments_dict(
            tmp_path, no_cfg_project.project_name, set_as_defaults=False
        )

        no_cfg_project.make_config_file(**changed_configs)
        self.check_config_reopen_and_check_config_again(
            no_cfg_project, changed_configs
        )

    # Test Update Config File
    # -------------------------------------------------------------

    def test_update_config_file__(self, no_cfg_project, tmp_path):
        """
        Set the configs as default, and then update them to
        new configs and check they are updated properly.

        Then, update only a subset (back to the defaults) and
        check only the subset is updated.
        """
        default_configs = test_utils.get_test_config_arguments_dict(
            tmp_path, no_cfg_project.project_name, set_as_defaults=True
        )

        no_cfg_project.make_config_file(**default_configs)
        project = no_cfg_project

        not_set_configs = test_utils.get_test_config_arguments_dict(
            tmp_path, project.project_name, set_as_defaults=False
        )

        test_utils.move_some_keys_to_end_of_dict(not_set_configs)

        # ensure Path is converted to str
        not_set_configs["local_path"] = str(not_set_configs["local_path"])

        project.update_config_file(**not_set_configs)

        test_utils.check_configs(project, not_set_configs)

        # Now update only a subset and check only this subset is updated.
        keys_to_not_update = [
            "local_path",
            "connection_method",
            "central_host_id",
            "central_host_username",
        ]

        for key in keys_to_not_update:
            default_configs.pop(key)

        project.update_config_file(**default_configs)

        for key in keys_to_not_update:
            default_configs[key] = not_set_configs[key]

        test_utils.check_configs(project, default_configs)

    def test_existing_projects(self, monkeypatch, tmp_path):
        """
        Test existing projects are correctly found based on whether
        they exist in the home directory and contain a config.yaml.

        By default, datashuttle saves project folders to
        Path.home() / .datashuttle. In order to not mess with
        the home directory during this test the `get_datashuttle_path()`
        function is monkeypatched in order to point to a tmp_path.

        The tmp_path / "projects" is filled with a mix of project folders
        with and without config, and tested against accordingly. The `local_path`
        and `central_path` specified in the DataShuttle config are arbitrarily put in
        `tmp_path`.
        """

        def patch_get_datashuttle_path():
            return tmp_path / "projects"

        monkeypatch.setattr(
            "datashuttle.configs.canonical_folders.get_datashuttle_path",
            patch_get_datashuttle_path,
        )

        project_1 = DataShuttle("project_1")
        project_1.make_config_file(
            tmp_path / "project_1",
            tmp_path / "project_1",
            "local_filesystem",
        )

        # project 2 will not be found, because it does not
        # have a config file.
        os.mkdir(tmp_path / "projects" / "project_2")

        project_2 = DataShuttle("project_3")
        project_2.make_config_file(
            tmp_path / "project_3",
            tmp_path / "project_3",
            "local_filesystem",
        )

        project_paths = getters.get_existing_project_paths()

        assert sorted(project_paths) == [
            (tmp_path / "projects" / "project_1"),
            (tmp_path / "projects" / "project_3"),
        ]

    # --------------------------------------------------------------------------------------------------------------------
    # Utils
    # --------------------------------------------------------------------------------------------------------------------

    def check_config_reopen_and_check_config_again(self, project, *kwargs):
        """
        Check the config file and project.cfg against provided kwargs,
        delete the project and set up the project again,
        checking everything is loaded correctly.
        """
        test_utils.check_configs(project, kwargs[0])
        project_name = project.project_name

        del project  # del project is almost certainly unnecessary

        project = DataShuttle(project_name)

        test_utils.check_configs(project, kwargs[0])
