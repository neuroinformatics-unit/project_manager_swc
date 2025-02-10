from __future__ import annotations

from typing import TYPE_CHECKING, List, Literal, Optional

if TYPE_CHECKING:

    from textual.app import ComposeResult

    from datashuttle.tui.interface import Interface


from textual import on
from textual.containers import Container, Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import (
    Button,
    Checkbox,
    Label,
    SelectionList,
    Static,
)
from textual.widgets.selection_list import Selection

# --------------------------------------------------------------------------------------
# Select Displayed Datatypes Screen
# --------------------------------------------------------------------------------------


class DisplayedDatatypesScreen(ModalScreen):
    """ """

    def __init__(
        self,
        create_or_transfer: Literal["create", "transfer"],
        interface: Interface,
    ) -> None:
        super(DisplayedDatatypesScreen, self).__init__()

        self.interface = interface
        self.create_or_transfer = create_or_transfer

        # TODO: this is copy and paste. TODO: move this to save thing as checkboxes.
        if self.create_or_transfer == "create":
            self.settings_key = "create_checkboxes_on"
        else:
            self.settings_key = "transfer_checkboxes_on"

        self.datatype_config = self.interface.get_tui_settings()[
            self.settings_key
        ]

    def compose(self) -> ComposeResult:

        selections = [
            Selection(datatype, idx, setting["displayed"])
            for idx, (datatype, setting) in enumerate(
                self.datatype_config.items()
            )
        ]
        yield Container(
            Vertical(
                Label(
                    "Select datatype checkboxes to display:",
                    id="display_datatypes_toplevel_label",  # TODO: CHANGE NAME
                ),
                SelectionList[int](
                    *selections, id="displayed_datatypes_selection_list"
                ),
                id="display_datatypes_selection_container",
            ),
            Vertical(),
            Horizontal(
                #       Button(
                #          "Save", id="display_datatypes_save_button"
                #     ),  #    TODO: CHANGE NAME
                Horizontal(),
                Button("Close", id="displayed_datatypes_close_button"),
                id="displayed_datatypes_button_container",
            ),
            id="display_datatypes_screen_container",
        )

    def on_button_pressed(self, event):
        """
        For some reason had issues unless did all together, could not save
        dynamically. should be clear with the 'Save' button.
        """
        if event.button.id == "displayed_datatypes_close_button":
            self.dismiss()

    def on_selection_list_selection_toggled(
        self, event
    ):  # SelectionMessage I think
        """ """
        datatype_name = event.selection.prompt.plain
        is_checked = not event.selection.initial_state
        self.datatype_config[datatype_name]["displayed"] = is_checked

        if not is_checked:
            self.datatype_config[datatype_name]["on"] = False

        self.interface.update_tui_settings(
            self.datatype_config, self.settings_key
        )


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

    def __init__(
        self,
        interface: Interface,
        create_or_transfer: Literal["create", "transfer"] = "create",
        id: Optional[str] = None,
    ) -> None:
        super(DatatypeCheckboxes, self).__init__(id=id)

        self.interface = interface
        self.create_or_transfer = create_or_transfer

        if self.create_or_transfer == "create":
            self.settings_key = "create_checkboxes_on"
        else:
            self.settings_key = "transfer_checkboxes_on"

        # `datatype_config` is basically just a convenience wrapper
        # around interface.get_tui_settings...
        self.datatype_config = self.interface.get_tui_settings()[
            self.settings_key
        ]

    def compose(self) -> ComposeResult:
        for datatype_name, datatype_setting in self.datatype_config.items():
            if datatype_setting["displayed"]:
                yield Checkbox(
                    datatype_name.replace("_", " "),
                    id=self.get_checkbox_name(datatype_name),
                    value=datatype_setting["on"],
                )

    @on(Checkbox.Changed)
    def on_checkbox_changed(self) -> None:
        """
        When a checkbox is changed, update the `self.datatype_config`
        to contain new boolean values for each datatype. Also update
        the stored `persistent_settings`.

        TODO: document this better. It is quite counter-intuitive because
        we update everything for a single change. BUT it is better to compartmentalise
        and doesn't incur any additional overhead. BUT check this is actually true
        there is probably as better way
        """
        for datatype in self.datatype_config.keys():
            if self.datatype_config[datatype]["displayed"]:
                self.datatype_config[datatype]["on"] = self.query_one(
                    f"#{self.get_checkbox_name(datatype)}"
                ).value

        self.interface.update_tui_settings(
            self.datatype_config, self.settings_key
        )

    def selected_datatypes(self) -> List[str]:
        """
        Get the names of the datatype options for which the
        checkboxes are switched on.
        """
        selected_datatypes = [
            datatype
            for datatype, settings in self.datatype_config.items()
            if settings["on"]
        ]
        return selected_datatypes

    def get_checkbox_name(self, datatype):
        return f"{self.create_or_transfer}_{datatype}_checkbox"
