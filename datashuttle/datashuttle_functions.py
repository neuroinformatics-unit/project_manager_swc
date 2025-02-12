from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datashuttle.utils.custom_types import DisplayMode
from pathlib import Path
from typing import (
    Literal,
    Optional,
)

from datashuttle.configs import (
    canonical_configs,
)
from datashuttle.configs.config_class import Configs
from datashuttle.utils import (
    validation,
)

# TODO
# ----
# add print as an output option
# add new stream to get all validation errors separated by \n
# add tests
# add docs

# on another PR
# improve validation - there are a few missed cases
# add validation to TUI

# Then just the docs rewrite!


# TODO: add 'print' option
def quick_validate_project(
    project_path: str | Path,
    top_level_folder: Optional[Literal["rawdata", "derivatives"]] = None,
    display_mode: DisplayMode = "warn",
    name_templates: Optional[dict] = None,
):
    """ """
    # TODO: search for top level folders and raise if not exist
    # assert rawdata or derivatives here
    rawdata_and_derivatives = ["rawdata", "derivatives"]
    project_path = Path(project_path)

    if not project_path.is_dir():
        raise FileNotFoundError(
            f"No file or folder found at `project_path`: {project_path}"
        )

    if (
        not (project_path / "rawdata").is_dir()
        or not (project_path / "derivatives").is_dir()
    ):
        raise FileNotFoundError(
            "`project_path` must contain a 'rawdata' or 'derivatives' folder."
        )

    if top_level_folder is None:
        top_level_folders_to_validate = rawdata_and_derivatives
    else:
        if top_level_folder not in rawdata_and_derivatives:
            raise ValueError(
                f"`top_level_folder must be one of: {rawdata_and_derivatives}"
            )
        top_level_folders_to_validate = [top_level_folder]

    placeholder_configs = {
        key: None for key in canonical_configs.get_canonical_configs().keys()
    }
    placeholder_configs["local_path"] = Path(project_path)  # type: ignore

    cfg = Configs(
        project_name=project_path.name,
        file_path=None,  # type: ignore
        input_dict=placeholder_configs,
    )

    for folder in top_level_folders_to_validate:
        validation.validate_project(
            cfg=cfg,
            top_level_folder=folder,  # type: ignore
            local_only=True,
            display_mode=display_mode,
            name_templates=name_templates,
        )
