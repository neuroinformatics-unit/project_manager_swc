from __future__ import annotations

from typing import TYPE_CHECKING, Iterable, List, Optional, cast

if TYPE_CHECKING:
    from textual import events

from dataclasses import dataclass
from pathlib import Path

import pyperclip
from rich.style import Style
from rich.text import Text
from textual._segment_tools import line_pad
from textual.message import Message
from textual.strip import Strip
from textual.widgets import (
    Checkbox,
    DirectoryTree,
    Input,
    Select,
    Static,
    TabPane,
)

from datashuttle.configs import canonical_folders

# --------------------------------------------------------------------------------------
# DatatypeCheckboxes
# --------------------------------------------------------------------------------------


class DatatypeCheckboxes(Static):
    """
    Dynamically-populated checkbox widget for convenient datatype
    selection during folder creation.

    Parameters
    ----------

    settings_key : 'create' if datatype checkboxes for the create tab,
                   'transfer' for the transfer tab. Transfer tab includes
                   additional datatype options (e.g. "all").

    Attributes
    ----------

    datatype_config : a Dictionary containing datatype as key (e.g. "ephys", "behav")
                      and values are `bool` indicating whether the checkbox is on / off.
                      If 'transfer', then transfer datatype arguments (e.g. "all")
                      are also included. This structure mirrors
                      the `persistent_settings` dictionaries.
    """

    def __init__(self, project, create_or_transfer="create"):
        super(DatatypeCheckboxes, self).__init__()

        self.project = project

        if create_or_transfer == "create":
            self.settings_key = "create_checkboxes_on"
        else:
            self.settings_key = "transfer_checkboxes_on"

        self.datatype_config = self.project._load_persistent_settings()["tui"][
            self.settings_key
        ]

    def compose(self):
        for datatype in self.datatype_config.keys():
            yield Checkbox(
                datatype.title(),
                id=f"tabscreen_{datatype}_checkbox",
                value=self.datatype_config[datatype],
            )

    def on_checkbox_changed(self):
        """
        When a checkbox is changed, update the `self.datatype_config`
        to contain new boolean values for each datatype. Also update
        the stored `persistent_settings`.
        """
        for datatype in self.datatype_config.keys():
            self.datatype_config[datatype] = self.query_one(
                f"#tabscreen_{datatype}_checkbox"
            ).value

        # This is slightly wasteful as update entire dict instead
        # of changed entry, but is negligible.
        persistent_settings = self.project._load_persistent_settings()
        persistent_settings["tui"][self.settings_key] = self.datatype_config
        self.project._save_persistent_settings(persistent_settings)

    def selected_datatypes(self) -> List[str]:
        """
        Get the names of the datatype options for which the
        checkboxes are switched on.
        """
        selected_datatypes = [
            datatype
            for datatype, is_on in self.datatype_config.items()
            if is_on
        ]
        return selected_datatypes


# --------------------------------------------------------------------------------------
# ClickableInput
# --------------------------------------------------------------------------------------


class ClickableInput(Input):
    """
    An input widget which emits a `ClickableInput.Clicked`
    signal when clicked, containing the input name
    `input` and mouse button index `button`.
    """

    @dataclass
    class Clicked(Message):
        input: ClickableInput
        button: int

    def __init__(
        self,
        mainwindow,
        placeholder,
        id=None,
        validate_on=None,
        validators=None,
    ):
        super(ClickableInput, self).__init__(
            placeholder=placeholder,
            id=id,
            validate_on=validate_on,
            validators=validators,
        )

        self.mainwindow = mainwindow

    def _on_click(self, event: events.Click) -> None:
        self.post_message(self.Clicked(self, event.button))

    def as_names_list(self):
        return self.value.replace(" ", "").split(",")

    def on_key(self, event):
        if event.key == "ctrl+q":
            pyperclip.copy(self.value)

        elif event.key == "ctrl+o":
            self.mainwindow.handle_open_filesystem_browser(Path(self.value))


# --------------------------------------------------------------------------------------
# CustomDirectoryTree
# --------------------------------------------------------------------------------------


class CustomDirectoryTree(DirectoryTree):
    @dataclass
    class DirectoryTreeSpecialKeyPress(Message):
        key: str
        node_path: Optional[Path]

    def __init__(self, mainwindow, path, id=None):
        super(CustomDirectoryTree, self).__init__(path=path, id=id)

        self.mainwindow = mainwindow

    def filter_paths(self, paths: Iterable[Path]) -> Iterable[Path]:
        """
        Filter out the top level .datashuttle folder than contains logs from
        the directorytree display.

        `paths` below are only the folders within the root folder. So this will
        filter out .datashuttle only at the root and not all instances of
        .datashuttle lower down which I suppose we may want visible.
        """
        return [
            path for path in paths if not path.name.startswith(".datashuttle")
        ]

    def on_key(self, event: events.Key):
        """
        Handle key presses on the CustomDirectoryTree. Depending on the keys pressed,
        copy the path under the cursor, refresh the directorytree or
        emit a DirectoryTreeSpecialKeyPress event.
        """
        if event.key == "ctrl+q":
            path_ = self.get_node_at_line(self.hover_line).data.path
            pyperclip.copy(path_.as_posix())

        elif event.key == "ctrl+o":
            path_ = self.get_node_at_line(self.hover_line).data.path
            self.mainwindow.handle_open_filesystem_browser(path_)

        elif event.key == "ctrl+r":
            self.post_message(
                self.DirectoryTreeSpecialKeyPress(event.key, node_path=None)
            )

        elif event.key in ["ctrl+a", "ctrl+f"]:
            path_ = self.get_node_at_line(self.hover_line).data.path
            self.post_message(
                self.DirectoryTreeSpecialKeyPress(event.key, node_path=path_)
            )

    # Overridden Methods
    # ----------------------------------------------------------------------------------

    def _render_line(
        self, y: int, x1: int, x2: int, base_style: Style
    ) -> Strip:
        """
        This function is overridden from textual's `Tree` class to stop
        CSS styling on hovering and clicking which was distracting /
        changed the default color used for transfer status, respectively.

        Note better approaches should be possible, see textual issue #4028.
        """
        tree_lines = self._tree_lines
        width = self.size.width

        if y >= len(tree_lines):
            return Strip.blank(width, base_style)

        line = tree_lines[y]

        is_hover = self.hover_line >= 0 and any(
            node._hover for node in line.path
        )

        cache_key = (
            y,
            is_hover,
            width,
            self._updates,
            self._pseudo_class_state,
            tuple(node._updates for node in line.path),
        )
        if cache_key in self._line_cache:
            strip = self._line_cache[cache_key]
        else:
            base_guide_style = self.get_component_rich_style(
                "tree--guides", partial=True
            )
            guide_hover_style = base_guide_style
            #            guide_hover_style = base_guide_style +
            #            self.get_component_rich_style(
            #               "tree--guides-hover", partial=True
            #          )
            guide_selected_style = (
                base_guide_style
                + self.get_component_rich_style(
                    "tree--guides-selected", partial=True
                )
            )

            hover = line.path[0]._hover
            selected = line.path[0]._selected and self.has_focus

            def get_guides(style: Style) -> tuple[str, str, str, str]:
                """Get the guide strings for a given style.

                Args:
                    style: A Style object.

                Returns:
                    Strings for space, vertical, terminator and cross.
                """
                lines: tuple[
                    Iterable[str], Iterable[str], Iterable[str], Iterable[str]
                ]
                if self.show_guides:
                    lines = self.LINES["default"]
                    if style.bold:
                        lines = self.LINES["bold"]
                    elif style.underline2:
                        lines = self.LINES["double"]
                else:
                    lines = ("  ", "  ", "  ", "  ")

                guide_depth = max(0, self.guide_depth - 2)
                guide_lines = tuple(
                    f"{characters[0]}{characters[1] * guide_depth} "  # type: ignore
                    for characters in lines
                )
                return cast("tuple[str, str, str, str]", guide_lines)

            if is_hover:
                line_style = self.get_component_rich_style(
                    "tree--highlight-line"
                )
            else:
                line_style = base_style

            guides = Text(style=line_style)
            guides_append = guides.append

            guide_style = base_guide_style
            for node in line.path[1:]:
                if hover:
                    guide_style = guide_hover_style
                if selected:
                    guide_style = guide_selected_style

                space, vertical, _, _ = get_guides(guide_style)
                guide = space if node.is_last else vertical
                if node != line.path[-1]:
                    guides_append(guide, style=guide_style)
                hover = hover or node._hover
                selected = (selected or node._selected) and self.has_focus

            if len(line.path) > 1:
                _, _, terminator, cross = get_guides(guide_style)
                if line.last:
                    guides.append(terminator, style=guide_style)
                else:
                    guides.append(cross, style=guide_style)

            label_style = self.get_component_rich_style(
                "tree--label", partial=True
            )
            if self.hover_line == y:
                label_style += self.get_component_rich_style(
                    "tree--highlight", partial=True
                )
            #            if self.cursor_line == y:
            #               label_style += self.get_component_rich_style(
            #                  "tree--cursor", partial=False
            #             )

            label = self.render_label(
                line.path[-1], line_style, label_style
            ).copy()
            label.stylize(Style(meta={"node": line.node._id, "line": y}))
            guides.append(label)

            segments = list(guides.render(self.app.console))
            pad_width = max(self.virtual_size.width, width)
            segments = line_pad(
                segments, 0, pad_width - guides.cell_len, line_style
            )
            strip = self._line_cache[cache_key] = Strip(segments)

        strip = strip.crop(x1, x2)
        return strip


# --------------------------------------------------------------------------------------
# TreeAndInputTab
# --------------------------------------------------------------------------------------


class TreeAndInputTab(TabPane):
    """
    A parent class that defined common methods for screens with
    a directory tree and sub / session inputs, .e. the Create tab
    and the Transfer tab.
    """

    def handle_fill_input_from_directorytree(
        self, sub_input_key, ses_input_key, event
    ):
        """
        When a CustomDirectoryTree key is pressed, we typically
        want to perform an action that involves an Input. These are
        coordinated here. Note that the 'copy' and 'refresh'
        features of the tree is handled at the level of the
        CustomDirectoryTree.

        Event Keys
        ----------

        "ctrl+a" : When CTRL and A are held at the same time, the sub / ses
                   node under the mouse is appended to the relevant Input

        "ctrl+f" : When CTRL and F are held at the same time, the sub / ses node
                  under the mouse is filled into the relevant Input (i.e. previous
                  value deleted).

        Parameters
        ----------

        sub_input_key : str
            The textual widget id for the subject input (prefixed with #)

        ses_input_key : str
            The textual widget id for the session input (prefixed with #)

        event : DirectoryTreeSpecialKeyPress
            A DirectoryTreeSpecialKeyPress event triggered from the
            CustomDirectoryTree.
        """
        if event.key == "ctrl+a":
            self.append_sub_or_ses_name_to_input(
                sub_input_key,
                ses_input_key,
                name=event.node_path.stem,
            )
        elif event.key == "ctrl+f":
            self.insert_sub_or_ses_name_to_input(
                sub_input_key,
                ses_input_key,
                name=event.node_path.stem,
            )

    def insert_sub_or_ses_name_to_input(
        self, sub_input_key, ses_input_key, name
    ):
        """
        see `handle_directorytree_key_pressed` for `sub_input_key` and
        `ses_input_key`.

        name : str
            The sub or ses name to append to the input.
        """
        if name.startswith("sub-"):
            self.query_one(sub_input_key).value = name
        elif name.startswith("ses-"):
            self.query_one(ses_input_key).value = name

    def append_sub_or_ses_name_to_input(
        self, sub_input_key, ses_input_key, name
    ):
        """
        see `insert_sub_or_ses_name_to_input`.
        """
        if name.startswith("sub-"):
            if not self.query_one(sub_input_key).value:
                self.query_one(sub_input_key).value = name
            else:
                self.query_one(sub_input_key).value += f", {name}"

        if name.startswith("ses-"):
            if not self.query_one(ses_input_key).value:
                self.query_one(ses_input_key).value = name
            else:
                self.query_one(ses_input_key).value += f", {name}"

    def get_sub_ses_names_and_datatype(self, sub_input_key, ses_input_key):
        """
        see `handle_fill_input_from_directorytree` for parameters.
        """
        sub_names = self.query_one(sub_input_key).as_names_list()
        ses_names = self.query_one(ses_input_key).as_names_list()
        datatype = self.query_one("DatatypeCheckboxes").selected_datatypes()

        return sub_names, ses_names, datatype


class TopLevelFolderSelect(Select):
    def __init__(self, project, existing_only, id):
        self.project = project

        top_level_folders = [
            (folder, folder)
            for folder in canonical_folders.get_top_level_folders()
        ]

        if existing_only:
            top_level_folders = [
                folders_tuple
                for folders_tuple in top_level_folders
                if (self.project.get_local_path() / folders_tuple[0]).exists()
            ]

        if id == "tabscreen_toplevel_select":
            self.settings_key = "create_tab"
        elif id == "transfer_toplevel_select":
            self.settings_key = "toplevel_transfer"
        elif id == "transfer_custom_select":
            self.settings_key = "custom_transfer"
        else:
            raise ValueError(
                "TopLevelSelect id not recognised. Must be matched to"
                "a persistent settings field"
            )

        value = self.get_top_level_folder_from_file()

        super(TopLevelFolderSelect, self).__init__(
            top_level_folders, value=value, id=id, allow_blank=True
        )

    def get_displayed_top_level_folder(self):
        assert self.value in canonical_folders.get_top_level_folders()
        return self.value

    def get_top_level_folder_from_file(self):
        persistent_settings = self.project._load_persistent_settings()
        top_level_folder = persistent_settings["tui"][
            "top_level_folder_select"
        ][self.settings_key]
        return top_level_folder

    def get_top_level_folder(self):
        top_level_folder = self.get_top_level_folder_from_file()
        assert (
            top_level_folder == self.get_displayed_top_level_folder()
        ), "config and widget should never be out of sync."  # TODO: should be tested in a dedicated unit test.
        return top_level_folder

    def on_select_changed(self, event):
        top_level_folder = event.value
        persistent_settings = self.project._load_persistent_settings()
        persistent_settings["tui"]["top_level_folder_select"][
            self.settings_key
        ] = top_level_folder
        self.project._save_persistent_settings(persistent_settings)
