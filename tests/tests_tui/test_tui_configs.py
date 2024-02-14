import copy
from pathlib import Path

import pytest
import test_utils

# https://stackoverflow.com/questions/55893235/pytest-skips-test-saying-asyncio-not
# -installed add to configs
# TODO: do we need to show anything when create folders is clicked?
# TODO: carefully check configs tests after refactor!
# TODO: need to allow name templates to be sub oR ses
# TODO: add green to light mode css
# TODO: could do CTRL+D to input to delete all content .
# test mainmenu button
# test with ssh
# test without ssh
# test bad ssh
# test some configs errors
# TODO: ssh setup not tested, need images!
# test all create files at once
# test all keyboard shortcuts
# test template validation settings etc.
# Settings
# Light / Dark mode
# DirectoryTree Setting
# TODO: don't bother testing tree highlgihting yet.
from tui_base import TuiBase

from datashuttle.tui.app import TuiApp
from datashuttle.tui.screens.modal_dialogs import (
    SelectDirectoryTreeScreen,
)
from datashuttle.tui.screens.project_manager import ProjectManagerScreen


class TestTuiConfigs(TuiBase):

    @pytest.mark.asyncio
    @pytest.mark.parametrize("kwargs_set", [1, 2])
    async def test_make_new_project_configs(
        self,
        empty_project_paths,
        kwargs_set,
    ):
        """
        Check the ConfigsContent when making a new project. This contains
        many widgets shared with the ConfigsContent on the tab page, however also
        includes an additional information banner and input for the project name.

        Here check these widgets are display correctly, and fill them. Next
        check the config widgets are empty, then fill the widgets, save,
        and check the interface.project and saved configs match the new
        settings.
        """
        tmp_config_path, tmp_path, project_name = empty_project_paths.values()

        kwargs = {
            "local_path": (tmp_path / "local" / project_name).as_posix(),
            # not used in TUI, set to `make_config_file` defaults.
            "central_path": (tmp_path / "central" / project_name).as_posix(),
            "show_transfer_progress": False,
        }

        if kwargs_set == 1:
            kwargs.update(
                {
                    "connection_method": "local_filesystem",
                    "central_host_id": None,
                    "central_host_username": None,
                    "overwrite_old_files": False,
                }
            )
        elif kwargs_set == 2:
            kwargs.update(
                {
                    "connection_method": "ssh",
                    "central_host_id": "@test.host.id",
                    "central_host_username": "test_username",
                    "overwrite_old_files": True,
                }
            )

        Path(kwargs["local_path"]).parent.mkdir(parents=True)
        Path(kwargs["central_path"]).parent.mkdir(parents=True)

        app = TuiApp()
        async with app.run_test() as pilot:

            # Select a new project, check NewProjectScreen is displayed correctly.
            await self.scroll_to_click_pause(
                pilot, "#mainwindow_new_project_button"
            )

            # Get the ConfigsContent and check all configs are displayed correctly.
            # `check_new_project_configs` checks empty defaults are displayed,
            # then updates with the kwargs and checks.
            configs_content = pilot.app.screen.query_one(
                "#new_project_configs_content"
            )

            await self.check_new_project_configs(
                pilot, project_name, configs_content, kwargs
            )

            # Save the configs and check the correct messages are shown.
            await self.scroll_to_click_pause(
                pilot,
                "#configs_save_configs_button",
            )

            assert (
                pilot.app.screen.query_one(
                    "#messagebox_message_label"
                ).renderable._text[0]
                == "A DataShuttle project has now been created.\n\n Click 'OK' to "
                "proceed to the project page, where you will be able to create and "
                "transfer project folders."
            )
            await self.close_messagebox(pilot)

            assert isinstance(pilot.app.screen, ProjectManagerScreen)

            # After saving, check all configs are correct on the DataShuttle
            # instance as well as the stored configs.
            test_utils.check_configs(
                pilot.app.screen.interface.project,
                kwargs,
                tmp_config_path / project_name / "config.yaml",
            )
            assert (
                pilot.app.screen.interface.project.project_name == project_name
            )

            await pilot.pause()

    async def check_new_project_configs(
        self, pilot, project_name, configs_content, kwargs
    ):
        """
        Check the configs displayed on the TUI match those founds in `kwargs`.
        Also, check the widgets unique to ConfigsContent on the configs selection
        for a new project.
        """
        # Project Name --------------------------------------------------------

        await self.fill_input(pilot, "#configs_name_input", project_name)
        assert (
            configs_content.query_one("#configs_name_input").value
            == project_name
        )

        # Shared Config Widgets -----------------------------------------------

        default_kwargs = {
            "local_path": "",
            "central_path": "",
            "connection_method": "local_filesystem",
            "overwrite_old_files": False,
        }
        await self.check_configs_widgets_match_configs(
            configs_content, default_kwargs
        )
        await self.set_configs_content_widgets(pilot, configs_content, kwargs)
        await self.check_configs_widgets_match_configs(configs_content, kwargs)

        await pilot.pause()

    @pytest.mark.asyncio
    async def test_configs_select_path(self, monkeypatch):
        """
        Test the 'Select' buttons / DirectoryTree on the ConfigsContent.
        These are used to select folders that are filled into the Input.
        Open the select dialog, select a folder, check the path is
        filled into the Input. There is one for both local
        and central path.

        When SSH is selected, the central path 'Select' should be disabled,
        as it only makes sense to choose this for local filesystem transfer.
        """
        self.monkeypatch_print(monkeypatch)

        app = TuiApp()
        async with app.run_test() as pilot:

            # Select the page and ConfigsContent for setting up new project
            await self.scroll_to_click_pause(
                pilot, "#mainwindow_new_project_button"
            )

            configs_content = pilot.app.screen.query_one(
                "#new_project_configs_content"
            )

            local_path_button = pilot.app.screen.query_one(
                "#configs_local_path_select_button"
            )
            central_path_button = pilot.app.screen.query_one(
                "#configs_central_path_select_button"
            )

            # For central and local path selects, click the button, select
            # the first folder from the DirectoryTree and check the input is filled.
            for select_button, path_input_id in zip(
                [local_path_button, central_path_button],
                ["#configs_local_path_input", "#configs_central_path_input"],
            ):
                await self.scroll_to_click_pause(
                    pilot,
                    f"#{select_button.id}",
                )

                assert isinstance(pilot.app.screen, SelectDirectoryTreeScreen)

                tree = pilot.app.screen.query_one(
                    "#select_directory_tree_directory_tree"
                )
                root_path = tree.root.data.path

                import time

                pilot.app.screen.prev_click_time = time.time()
                pilot.app.screen.on_directory_tree_directory_selected(
                    tree.root.data
                )
                await pilot.pause()

                assert (
                    configs_content.query_one(path_input_id).value
                    == root_path.as_posix()
                )

                await pilot.pause()

            # Check the central path only is disabled in SSH mode.
            assert local_path_button.disabled is False
            assert central_path_button.disabled is False

            await self.scroll_to_click_pause(pilot, "#configs_ssh_radiobutton")

            assert local_path_button.disabled is False
            assert central_path_button.disabled is True

            await pilot.pause()

    @pytest.mark.asyncio
    async def test_update_config_on_project_manager_screen(
        self, setup_project_paths
    ):
        """
        Test the ConfigsContent on the project manager tab screen.
        The project is set up in the fixture, navigate to the project page.
        Check that the default configs are displayed. Change all the configs,
        save, and check these are updated on the config file and on the
        `project` stored in `interface`.

        Next, exit out of the project with the "Main Menu" button, go back
        into the project and check the new configs are displayed.
        """
        tmp_config_path, tmp_path, project_name = setup_project_paths.values()

        app = TuiApp()
        async with app.run_test() as pilot:

            # Navigate to the existing project and click onto the
            # configs tab.
            await self.check_and_click_onto_existing_project(
                pilot, project_name
            )

            await self.switch_tab(pilot, "configs")

            configs_content = pilot.app.screen.query_one(
                "#tabscreen_configs_content"
            )

            # Now get the default datashuttle configs, and check they match
            # those displayed on the ConfigsContent.
            project_cfg = copy.deepcopy(pilot.app.screen.interface.project.cfg)
            project_cfg.convert_str_and_pathlib_paths(
                project_cfg, "path_to_str"
            )  # TODO: this syntax is so weird.

            await self.check_configs_widgets_match_configs(
                configs_content, project_cfg
            )

            # Now we make some new settings, and set the ConfigsContent.
            # Make sure they are all different to the existing configs,
            # then save and check the configs on the DataShuttle instance
            # and file are updated.
            local_path = tmp_path / f"some-random-path/{project_name}"
            central_path = tmp_path / f"some-random-path2/{project_name}"

            local_path.mkdir(parents=True)
            central_path.mkdir(parents=True)

            new_kwargs = {
                "local_path": local_path.as_posix(),
                "central_path": central_path.as_posix(),
                "connection_method": "ssh",
                "central_host_id": "random_host",
                "central_host_username": "random_username",
                "overwrite_old_files": True,
            }

            for key in new_kwargs.keys():
                # The purpose is to update to completely new configs
                assert new_kwargs[key] != project_cfg[key]

            await self.set_configs_content_widgets(
                pilot, configs_content, new_kwargs
            )

            await self.check_configs_widgets_match_configs(
                configs_content, new_kwargs
            )

            await self.scroll_to_click_pause(
                pilot,
                "#configs_save_configs_button",
            )
            assert (
                pilot.app.screen.query_one(
                    "#messagebox_message_label"
                ).renderable._text[0]
                == "Configs saved."
            )
            await self.close_messagebox(pilot)

            test_utils.check_configs(
                pilot.app.screen.interface.project,
                new_kwargs,
                tmp_config_path / project_name / "config.yaml",
            )

            # Finally, use "Main Menu" button to go back to the home screen,
            # navigate back to the project and check the new configs are now
            # displayed.
            await self.scroll_to_click_pause(pilot, "#all_main_menu_buttons")
            assert pilot.app.screen.id == "_default"

            await self.check_and_click_onto_existing_project(
                pilot, project_name
            )
            await self.switch_tab(pilot, "transfer")
            configs_content = pilot.app.screen.query_one(
                "#tabscreen_configs_content"
            )
            await self.check_configs_widgets_match_configs(
                configs_content, new_kwargs
            )

            await pilot.pause()

    @pytest.mark.asyncio
    async def test_bad_configs_screen_input(self, empty_project_paths):

        app = TuiApp()
        async with app.run_test() as pilot:

            # Select a new project, check NewProjectScreen is displayed correctly.
            await self.scroll_to_click_pause(
                pilot, "#mainwindow_new_project_button"
            )

            await self.fill_input(pilot, "#configs_name_input", "a")
            await self.fill_input(pilot, "#configs_local_path_input", "a")
            await self.fill_input(pilot, "#configs_central_path_input", "b")
            await self.scroll_to_click_pause(
                pilot, "#configs_save_configs_button"
            )

            assert (
                "The central_path does not end in the project name: a"
                in pilot.app.screen.query_one(
                    "#messagebox_message_label"
                ).renderable._text[0]
            )

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    async def check_configs_widgets_match_configs(
        self, configs_content, kwargs
    ):
        """
        Check that the widgets of the TUI configs match those found
        in `kwargs`.
        """

        # Local Path ----------------------------------------------------------

        assert (
            configs_content.query_one("#configs_local_path_input").value
            == kwargs["local_path"]
        )

        # Connection Method ---------------------------------------------------

        label = (
            "SSH"
            if kwargs["connection_method"] == "ssh"
            else "Local Filesystem"
        )
        assert (
            configs_content.query_one(
                "#configs_connect_method_radioset"
            ).pressed_button.label._text[0]
            == label
        )

        if kwargs["connection_method"] == "ssh":

            # Central Host ID -------------------------------------------------

            assert (
                configs_content.query_one(
                    "#configs_central_host_id_input"
                ).value
                == kwargs["central_host_id"]
            )

            # Central Host Username -------------------------------------------

            assert (
                configs_content.query_one(
                    "#configs_central_host_username_input"
                ).value
                == kwargs["central_host_username"]
            )

        # Central Path --------------------------------------------------------

        assert (
            configs_content.query_one("#configs_central_path_input").value
            == kwargs["central_path"]
        )

        # Overwrite Old Files -------------------------------------------------

        assert (
            configs_content.query_one(
                "#configs_overwrite_files_checkbox"
            ).value
            is kwargs["overwrite_old_files"]
        )

    async def set_configs_content_widgets(
        self, pilot, configs_content, kwargs
    ):
        """
        Given a dict of options that can be set on the configs TUI
        in kwargs, set all configs widgets according to kwargs.
        """

        # Local Path ----------------------------------------------------------

        await self.fill_input(
            pilot, "#configs_local_path_input", kwargs["local_path"]
        )

        # Connection Method ---------------------------------------------------

        if kwargs["connection_method"] == "ssh":

            await self.scroll_to_click_pause(pilot, "#configs_ssh_radiobutton")

            # Central Host ID -------------------------------------------------

            await self.fill_input(
                pilot,
                "#configs_central_host_id_input",
                kwargs["central_host_id"],
            )

            # Central Host Username -------------------------------------------

            await self.fill_input(
                pilot,
                "#configs_central_host_username_input",
                kwargs["central_host_username"],
            )

        # Central Path --------------------------------------------------------

        await self.fill_input(
            pilot, "#configs_central_path_input", kwargs["central_path"]
        )

        # Overwrite Files -----------------------------------------------------

        if kwargs["overwrite_old_files"]:

            assert not configs_content.query_one(
                "#configs_overwrite_files_checkbox"
            ).value

            await self.scroll_to_click_pause(
                pilot,
                "#configs_overwrite_files_checkbox",
            )
