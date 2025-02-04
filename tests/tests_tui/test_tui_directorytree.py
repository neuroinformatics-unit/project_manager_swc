from pathlib import Path

import pyperclip
import pytest
from tui_base import TuiBase

from datashuttle.tui.app import TuiApp

try:
    pyperclip.paste()
    HAS_GUI = True
except pyperclip.PyperclipException:
    HAS_GUI = False


class TestTuiCreateDirectoryTree(TuiBase):
    """
    Test the `Create` tab directory tree.
    `Transfer`
    """

    @pytest.mark.asyncio
    async def test_fill_and_append_next_sub_and_ses(self, setup_project_paths):
        """
        Test the CTRL+F and CTRL+A functions on the directorytree
        that fill and append subject / session name to the inputs.
        """
        tmp_config_path, tmp_path, project_name = setup_project_paths.values()

        app = TuiApp()
        async with app.run_test(size=self.tui_size()) as pilot:

            # Open the create tab and first fill the subject
            # and session inputs with -001.
            await self.check_and_click_onto_existing_project(
                pilot, project_name
            )

            await self.fill_input(
                pilot, "#create_folders_subject_input", "sub-001"
            )
            await self.fill_input(
                pilot, "#create_folders_session_input", "ses-001"
            )

            # Create these folders, then press CTRL+A on
            # the created nodes on the filetree and check
            # they are appended to the input.
            await self.scroll_to_click_pause(
                pilot,
                "#create_folders_create_folders_button",
            )

            await self.reload_tree_nodes(
                pilot, "#create_folders_directorytree", 4
            )

            await self.hover_and_press_tree(
                pilot,
                "#create_folders_directorytree",
                hover_line=2,
                press_string="ctrl+a",
            )
            assert (
                pilot.app.screen.query_one(
                    "#create_folders_subject_input"
                ).value
                == "sub-001, sub-001"
            )

            await self.hover_and_press_tree(
                pilot,
                "#create_folders_directorytree",
                hover_line=3,
                press_string="ctrl+a",
            )
            assert (
                pilot.app.screen.query_one(
                    "#create_folders_session_input"
                ).value
                == "ses-001, ses-001"
            )

            # Now press CTRL+F, which will fill only a single
            # subject / session (removing the existing subject / session list).
            await self.hover_and_press_tree(
                pilot,
                "#create_folders_directorytree",
                hover_line=2,
                press_string="ctrl+f",
            )
            assert (
                pilot.app.screen.query_one(
                    "#create_folders_subject_input"
                ).value
                == "sub-001"
            )

            await self.hover_and_press_tree(
                pilot,
                "#create_folders_directorytree",
                hover_line=3,
                press_string="ctrl+f",
            )
            assert (
                pilot.app.screen.query_one(
                    "#create_folders_session_input"
                ).value
                == "ses-001"
            )

            await pilot.pause()

    @pytest.mark.skipif(HAS_GUI is False, reason="Requires system has GUI.")
    @pytest.mark.asyncio
    async def test_create_folders_directorytree_clipboard(
        self, setup_project_paths
    ):
        """
        Check that pressing CTRL+W on the directorytree copies the
        hovered folder to the clipboard (using pyperclip).
        """
        tmp_config_path, tmp_path, project_name = setup_project_paths.values()

        app = TuiApp()
        async with app.run_test(size=self.tui_size()) as pilot:
            await self.setup_existing_project_create_tab_filled_sub_and_ses(
                pilot, project_name, create_folders=True
            )

            await self.reload_tree_nodes(
                pilot, "#create_folders_directorytree", 4
            )
            pyperclip.copy("STARTING VAL")

            await self.hover_and_press_tree(
                pilot,
                "#create_folders_directorytree",
                hover_line=2,
                press_string="ctrl+q",
            )

            pasted_path = pyperclip.paste()

            assert (
                pasted_path
                == pilot.app.screen.query_one("#create_folders_directorytree")
                .get_node_at_line(2)
                .data.path.as_posix()
            )

            await pilot.pause()

    @pytest.mark.asyncio
    async def test_create_folders_directorytree_open_filesystem(
        self, setup_project_paths, monkeypatch
    ):
        """
        Test pressing CTRL+O on the filetree triggers the opening
        of a folder through the show-in-file-manager package
        (monkeypatched function).
        """
        tmp_config_path, tmp_path, project_name = setup_project_paths.values()

        app = TuiApp()
        async with app.run_test(size=self.tui_size()) as pilot:

            # Set up the 'create tab' with loaded nodes
            await self.setup_existing_project_create_tab_filled_sub_and_ses(
                pilot, project_name, create_folders=True
            )

            await self.reload_tree_nodes(
                pilot, "#create_folders_directorytree", 4
            )

            # Set up a monkeypatch function which will insert the path selected
            # when CTRL+O is pressed into an immutable object (signal)
            # Press the tree and check the function is triggered with
            # the correct path passed.
            signal = [Path()]

            def set_signal_to_path(path_):
                signal[0] = path_

            monkeypatch.setattr(
                "showinfm.show_in_file_manager", set_signal_to_path
            )

            assert signal[0] == Path()

            await self.hover_and_press_tree(
                pilot,
                "#create_folders_directorytree",
                hover_line=3,
                press_string="ctrl+o",
            )
            assert (
                signal[0]
                == pilot.app.screen.query_one("#create_folders_directorytree")
                .get_node_at_line(3)
                .data.path.as_posix()
            )

            await pilot.pause()
