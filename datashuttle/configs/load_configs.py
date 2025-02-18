import warnings
from pathlib import Path
from typing import Optional, Union

from datashuttle.configs import canonical_configs
from datashuttle.configs.config_class import Configs
from datashuttle.utils import utils
from datashuttle.utils.custom_exceptions import ConfigError

# -----------------------------------------------------------------------------
# Load Supplied Config
# -----------------------------------------------------------------------------


def attempt_load_configs(
    project_name: str,
    config_path: Path,
    verbose: bool = True,
) -> Optional[Configs]:
    """
    Try to load an existing config file, that was previously
    saved by Datashuttle. This should always work, unless
    not already initialised (prompt) or these have been
    changed manually.

    Parameters
    ----------
    project_name : name of project

    config_path : path to datashuttle config .yaml file

    verbose : warnings and error messages will be printed.
    """
    exists = config_path.is_file()

    if not exists:
        if verbose:
            warnings.warn(
                "Configuration file has not been initialized. "
                "Use make_config_file() to setup before continuing."
            )
        return None

    new_cfg: Optional[Configs]

    new_cfg = Configs(project_name, config_path, None)

    try:
        new_cfg.load_from_file()

    except BaseException:
        new_cfg = None

        utils.log_and_raise_error(
            f"Config file failed to load. Check file "
            f"formatting at {config_path.as_posix()}. If "
            f"cannot load, re-initialise configs with "
            f"make_config_file()",
            ConfigError,
        )

    return new_cfg


def convert_str_and_pathlib_paths(
    config_dict: Union["Configs", dict], direction: str
) -> None:
    """
    Config paths are stored as str in the .yaml but used as Path
    in the module, so make the conversion here.

    Parameters
    ----------

    config_dict : DataShuttle.cfg dict of configs
    direction : "path_to_str" or "str_to_path"
    """
    for path_key in canonical_configs.keys_str_on_file_but_path_in_class():
        value = config_dict[path_key]

        if value:
            if direction == "str_to_path":
                config_dict[path_key] = Path(value)

            elif direction == "path_to_str":
                if not isinstance(value, str):
                    config_dict[path_key] = value.as_posix()

            else:
                utils.log_and_raise_error(
                    "Option must be 'path_to_str' or 'str_to_path'",
                    ValueError,
                )
