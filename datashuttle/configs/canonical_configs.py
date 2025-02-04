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


def get_tui_config_defaults() -> Dict:
    """
    Get the default settings for the datatype checkboxes
    in the TUI. By default, they are all checked.
    """
    settings = {
        "tui": {
            "create_checkboxes_on": {
                "behav": True,
                "ephys": True,
                "funcimg": True,
                "anat": True,
            },
            "transfer_checkboxes_on": {
                "behav": False,
                "ephys": False,
                "funcimg": False,
                "anat": False,
                "all": True,
                "all_datatype": False,
                "all_non_datatype": False,
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
    return get_broad_datatypes() + get_narrow_datatypes()


def get_broad_datatypes():
    return ["ephys", "behav", "funcimg", "anat"]


def get_narrow_datatypes():
    return [
        # for "ephys",
        "ecephys",
        "icephys",
        # for "funcimg",
        "cscope",
        "f2pe",
        "fmri",
        "fusi",
        # for "anat",
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
    ]
