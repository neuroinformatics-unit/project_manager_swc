"""
This module contains all information for the required
format of the configs class. This is clearly defined
as configs can be provided from file or input dynamically
and so careful checks must be done.

If adding a new config, first add the key to
get_canonical_configs() and type to
get_canonical_configs()
"""

from __future__ import annotations

from typing import (
    TYPE_CHECKING,
    Dict,
    List,
    Literal,
    Optional,
    Union,
    get_args,
    get_origin,
)

if TYPE_CHECKING:
    from datashuttle.configs.config_class import Configs
import copy
from pathlib import Path

from datashuttle.utils import folders, utils
from datashuttle.utils.custom_exceptions import ConfigError


def get_canonical_configs() -> dict:
    """
    The only permitted types for DataShuttle
    config values.
    """
    canonical_configs = {
        "local_path": Union[str, Path],
        "central_path": Union[str, Path],
        "connection_method": Literal["ssh", "local_filesystem"],
        "central_host_id": Optional[str],
        "central_host_username": Optional[str],
    }

    return canonical_configs


# -----------------------------------------------------------------------------
# Check Configs
# -----------------------------------------------------------------------------


def check_dict_values_raise_on_fail(config_dict: Configs) -> None:
    """
    Central function for performing checks on a
    DataShuttle Configs UserDict class. This should
    be run after any change to the configs (e.g.
    make_config_file, update_config_file, supply_config_file).

    This will raise assert if condition is not met.

    Parameters
    ----------

    config_dict : datashuttle config UserDict
    """
    canonical_dict = get_canonical_configs()

    for key in canonical_dict.keys():
        if key not in config_dict.keys():
            utils.log_and_raise_error(
                f"Loading Failed. The key '{key}' was not "
                f"found in the config. "
                f"Config file was not updated.",
                ConfigError,
            )

    for key in config_dict.keys():
        if key not in canonical_dict.keys():
            utils.log_and_raise_error(
                f"The config contains an invalid key: {key}. "
                f"Config file was not updated.",
                ConfigError,
            )

    check_config_types(config_dict)

    if list(config_dict.keys()) != list(canonical_dict.keys()):
        utils.log_and_raise_error(
            f"New config keys are in the wrong order. The"
            f" order should be: {canonical_dict.keys()}.",
            ConfigError,
        )

    if config_dict["connection_method"] not in ["ssh", "local_filesystem"]:
        utils.log_and_raise_error(
            "'connection method' must be 'ssh' or 'local_filesystem'.",
            ConfigError,
        )

    for path_type in ["local_path", "central_path"]:
        raise_on_bad_path_syntax(config_dict[path_type].as_posix(), path_type)

    # Check SSH settings
    if config_dict["connection_method"] == "ssh" and (
        not config_dict["central_host_id"]
        or not config_dict["central_host_username"]
    ):
        utils.log_and_raise_error(
            "'central_host_id' and 'central_host_username' are "
            "required if 'connection_method' is 'ssh'.",
            ConfigError,
        )

    # Initialise the local project folder
    utils.print_message_to_user(
        f"Making project folder at: {config_dict['local_path']}"
    )
    try:
        folders.create_folders(config_dict["local_path"])
    except OSError:
        utils.log_and_raise_error(
            f"Could not make project folder at: {config_dict['local_path']}. "
            f"Config file not updated.",
            RuntimeError,
        )


def raise_on_bad_path_syntax(
    path_name: str,
    path_type: str,
) -> None:
    """
    Error if some common, unsupported patterns are observed
    (e.g. ~, .) for path.
    """
    if path_name[0] == "~":
        utils.log_and_raise_error(
            f"{path_type} must contain the full folder path "
            "with no ~ syntax.",
            ConfigError,
        )

    # pathlib strips "./" so not checked.
    for bad_start in [".", "../"]:
        if path_name.startswith(bad_start):
            utils.log_and_raise_error(
                f"{path_type} must contain the full folder path "
                "with no dot syntax.",
                ConfigError,
            )


def check_config_types(config_dict: Configs) -> None:
    """
    Check the type of passed configs matched canonical types.
    This is a sub-function of check_dict_values_raise_on_fail()

    Notes
    ------

    This is a little awkward as testing types against
    Union is not neat. To do this you can use
    isinstance(type, get_args(Union[types])).
    But get_args() will be empty if there is only
    one type in union. So we need to test the
    two cases explicitly.
    """
    required_types = get_canonical_configs()
    fail = False

    for key in config_dict.keys():
        expected_type = required_types[key]

        if get_origin(expected_type) is Literal:
            if config_dict[key] not in get_args(expected_type):
                utils.log_and_raise_error(
                    f"'{config_dict[key]}' not in {get_args(expected_type)}",
                    ConfigError,
                )

        elif len(get_args(required_types[key])) == 0:
            if not isinstance(config_dict[key], expected_type):
                fail = True
        else:
            if not isinstance(config_dict[key], get_args(expected_type)):
                fail = True

        if fail:
            utils.log_and_raise_error(
                f"The type of the value at '{key}' is incorrect, "
                f"it must be {expected_type}. "
                f"Config file was not updated.",
                ConfigError,
            )


# -----------------------------------------------------------------------------
# Persistent settings
# -----------------------------------------------------------------------------


# TODO: don't forget backward compatibility!
def get_tui_config_defaults() -> Dict:
    """
    Get the default settings for the datatype checkboxes
    in the TUI.

    Two sets are maintained (one for creating,
    one for transfer) which have different defaults.
    By default, all broad datatype checkboxes are displayed,
    and narrow are turned off.
    """
    settings = {
        "tui": {
            "create_checkboxes_on": {},
            "transfer_checkboxes_on": {
                "all": {"on": True, "displayed": True},
                "all_datatype": {"on": False, "displayed": True},
                "all_non_datatype": {"on": False, "displayed": True},
            },
            "top_level_folder_select": {
                "create_tab": "rawdata",
                "toplevel_transfer": "rawdata",
                "custom_transfer": "rawdata",
            },
            "bypass_validation": False,
            "overwrite_existing_files": "never",
            "dry_run": False,
        }
    }

    # Fill all datatype options
    for broad_key in get_broad_datatypes():

        settings["tui"]["create_checkboxes_on"][broad_key] = {  # type: ignore
            "on": True,
            "displayed": True,
        }
        settings["tui"]["transfer_checkboxes_on"][broad_key] = {  # type: ignore
            "on": False,
            "displayed": True,
        }

    for narrow_key in quick_get_narrow_datatypes():
        settings["tui"]["create_checkboxes_on"][narrow_key] = {  # type: ignore
            "on": False,
            "displayed": False,
        }
        settings["tui"]["transfer_checkboxes_on"][narrow_key] = {  # type: ignore
            "on": False,
            "displayed": False,
        }

    return settings


def get_name_templates_defaults() -> Dict:
    return {"name_templates": {"on": False, "sub": None, "ses": None}}


def get_persistent_settings_defaults() -> Dict:
    """
    Persistent settings are settings that are maintained
    across sessions. Currently, persistent settings for
    both the API and TUI are stored in the same place.

    Currently, settings for the working top level folder,
    TUI checkboxes and name templates (i.e. regexp
    validation for sub and ses names) are stored.
    """
    settings = {}
    settings.update(get_tui_config_defaults())
    settings.update(get_name_templates_defaults())

    return settings


def get_datatypes() -> List[str]:
    """
    Canonical list of datatype flags based on NeuroBlueprint.

    This must be kept up to date with the datatypes in the NeuroBLueprint specification.
    """
    return get_broad_datatypes() + quick_get_narrow_datatypes()


def get_broad_datatypes():
    return ["ephys", "behav", "funcimg", "anat"]


def get_narrow_datatypes():
    """
    Return the narrow datatype associated with each broad datatype.
    The mapping between broad and narrow datatypes is required for validation.
    """
    return {
        "ephys": ["ecephys", "icephys"],
        "funcimg": ["cscope", "f2pe", "fmri", "fusi"],
        "anat": [
            "2pe",
            "bf",
            "cars",
            "conf",
            "dic",
            "df",
            "fluo",
            "mpe",
            "nlo",
            "oct",
            "pc",
            "pli",
            "sem",
            "spim",
            "sr",
            "tem",
            "uct",
            "mri",
        ],
    }


def quick_get_narrow_datatypes():
    """
    A convenience wrapper around `get_narrow_datatypes()`
    to quickly get a list of all narrow datatypes.
    """
    all_narrow_datatypes = get_narrow_datatypes()
    top_level_keys = list(all_narrow_datatypes.keys())
    flat_narrow_datatypes = []

    for key in top_level_keys:
        flat_narrow_datatypes += all_narrow_datatypes[key]

    return flat_narrow_datatypes


def in_place_update_settings_for_narrow_datatype(settings: dict):
    """
    In versions < v0.6.0, only 'broad' datatypes were implemented
    and available in the TUI. Since, 'narrow' datatypes are introduced
    and datatype tui can be set to be both on / off but also
    displayed / not displayed.

    This function converts the old format to the new format so that
    all broad datatype settings (on / off) are maintained in
    then new version.
    """
    canonical_tui_configs = get_tui_config_defaults()

    new_create_checkbox_configs = copy.deepcopy(
        canonical_tui_configs["tui"]["create_checkboxes_on"]
    )
    new_transfer_checkbox_configs = copy.deepcopy(
        canonical_tui_configs["tui"]["transfer_checkboxes_on"]
    )

    for key in ["behav", "ephys", "funcimg", "anat"]:
        new_create_checkbox_configs[key]["on"] = settings["tui"][
            "create_checkboxes_on"
        ][key]
        new_transfer_checkbox_configs[key]["on"] = settings["tui"][
            "transfer_checkboxes_on"
        ][key]

    for key in ["all", "all_datatype", "all_non_datatype"]:
        new_transfer_checkbox_configs[key]["on"] = settings["tui"][
            "transfer_checkboxes_on"
        ][key]

    settings["tui"]["create_checkboxes_on"] = new_create_checkbox_configs
    settings["tui"]["transfer_checkboxes_on"] = new_transfer_checkbox_configs
