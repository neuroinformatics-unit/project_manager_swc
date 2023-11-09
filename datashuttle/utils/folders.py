from __future__ import annotations

from typing import TYPE_CHECKING, Dict

if TYPE_CHECKING:
    from datashuttle import DataShuttle
    from datashuttle.configs.config_class import Configs

import glob
import os
import warnings
from pathlib import Path
from typing import Any, List, Literal, Optional, Tuple, Union

from datashuttle.configs import canonical_folders, canonical_tags

from . import folders, formatting, ssh, utils

# -----------------------------------------------------------------------------
# Make Folders
# -----------------------------------------------------------------------------


def make_folder_trees(
    cfg: Configs,
    sub_names: Union[str, list],
    ses_names: Union[str, list],
    datatype: Union[List[str], str],
    log: bool = True,
) -> None:
    """
    Entry method to make a full folder tree. It will
    iterate through all passed subjects, then sessions, then
    subfolders within a datatype folder. This
    permits flexible creation of folders (e.g.
    to make subject only, do not pass session name.

    Ensure sub and ses names are already formatted
    before use in this function (see _start_log())

    Parameters
    ----------

    sub_names, ses_names, datatype : see make_folders()

    log : whether to log or not. If True, logging must
        already be initialised.
    """
    datatype_passed = datatype not in [[""], ""]

    if datatype_passed:
        formatting.check_datatype_is_valid(cfg, datatype, error_on_fail=True)

    for sub in sub_names:
        sub_path = cfg.make_path(
            "local",
            sub,
        )

        make_folders(sub_path, log)

        if datatype_passed:
            make_datatype_folders(cfg, datatype, sub_path, "sub")

        for ses in ses_names:
            ses_path = cfg.make_path(
                "local",
                [sub, ses],
            )

            make_folders(ses_path, log)

            if datatype_passed:
                make_datatype_folders(cfg, datatype, ses_path, "ses", log=log)


def make_datatype_folders(
    cfg: Configs,
    datatype: Union[list, str],
    sub_or_ses_level_path: Path,
    level: str,
    log: bool = True,
) -> None:
    """
    Make datatype folder (e.g. behav) at the sub or ses
    level. Checks folder_class.Folders attributes,
    whether the datatype is used and at the current level.

    Parameters
    ----------
    datatype : datatype (e.g. "behav", "all") to use. Use
        empty string ("") for none.

    sub_or_ses_level_path : Full path to the subject
        or session folder where the new folder
        will be written.

    level : The folder level that the
        folder will be made at, "sub" or "ses"

    log : whether to log on or not (if True, logging must
        already be initialised).
    """
    datatype_items = cfg.get_datatype_items(datatype)

    for datatype_key, datatype_folder in datatype_items:  # type: ignore
        if datatype_folder.level == level:
            datatype_path = sub_or_ses_level_path / datatype_folder.name

            make_folders(datatype_path, log)


# Make Folders Helpers --------------------------------------------------------


def make_folders(paths: Union[Path, List[Path]], log: bool = True) -> None:
    """
    For path or list of paths, make them if
    they do not already exist.

    Parameters
    ----------

    paths : Path or list of Paths to create

    log : if True, log all made folders. This
        requires the logger to already be initialised.
    """
    if isinstance(paths, Path):
        paths = [paths]

    for path_ in paths:
        if not path_.is_dir():
            path_.mkdir(parents=True)
            if log:
                utils.log(f"Made folder at path: {path_}")


def check_no_duplicate_sub_ses_key_values(
    project: DataShuttle,
    base_folder: Path,
    new_sub_names: List[str],
    new_ses_names: Optional[List[str]] = None,
) -> None:
    """
    Given a list of subject and optional session names,
    check whether these already exist in the local project
    folder.

    This uses search_sub_or_ses_level() to search the local
    folder and then checks for the putative new subject
    or session names to determine any matches.

    Parameters
    ----------

    project : initialised datashuttle project

    base_folder : local_path to search

    new_sub_names : list of subject names that are being
     checked for duplicates

    new_ses_names : list of session names that are being
     checked for duplicates
    """
    if new_ses_names == []:
        new_ses_names = None

    for new_sub in new_sub_names:
        existing_names = search_sub_or_ses_level(
            project.cfg, base_folder, "local", search_str="*sub-*"
        )[0]

        check_new_subject_does_not_duplicate_existing(
            new_sub, existing_names, "sub"
        )

    if new_ses_names is not None:
        for sub in new_sub_names:
            for new_ses in new_ses_names:
                existing_names = search_sub_or_ses_level(
                    project.cfg, base_folder, "local", sub, search_str="*ses-*"
                )[0]

                check_new_subject_does_not_duplicate_existing(
                    new_ses, existing_names, "ses"
                )


def check_new_subject_does_not_duplicate_existing(
    new_name: str, existing_names: List[str], prefix: Literal["sub", "ses"]
) -> None:
    """
    Check that a subject or session does not already exist
    that shares a sub / ses id with the new_name.

    When creating new subject or session files, if the
    sub or ses id already exists, the full subject or session
    name should match exactly.

    For example, if "sub-001" exists, we can pass
    "sub-001" as a valid subject name (for example, when making sessions).
    However, if "sub-001_another-tag" exists, we should throw an
    error, because this shares the same subject id but refers to
    a different subject.
    """
    # For every existing subject / session name,
    # check whether the id matches the new name. If it
    # does, add the full name to `matched_existing_names`.
    matched_existing_names = []
    for exist_name in existing_names:
        exist_name_id = utils.get_values_from_bids_formatted_name(
            [exist_name], prefix, return_as_int=True
        )[0]
        new_name_id = utils.get_values_from_bids_formatted_name(
            [new_name], prefix, return_as_int=True
        )[0]

        if exist_name_id == new_name_id:
            matched_existing_names.append(exist_name)

    # We expect either zero matches (subject or session with matching id
    # does not exist. We can pass this case, as file will be made).
    # If more than 1 duplicates already exist, raise.
    # If exactly one exists, check it matches the new name exactly. Otherwise,
    # it is a duplicate.
    if len(matched_existing_names) > 1:
        utils.log_and_raise_error(
            f"Cannot make folders. Multiple {prefix} ids exists: {matched_existing_names}. This should"
            f"never happen. Check the {prefix} ids and ensure unique {prefix} "
            f"ids (e.g. sub-001) appear only once."
        )

    if len(matched_existing_names) == 1:
        if new_name != matched_existing_names[0]:
            utils.log_and_raise_error(
                f"Cannot make folders. A {prefix} already exists with the same {prefix} id as {new_name}. "
                f"The existing folder is {matched_existing_names[0]}."
            )


# -----------------------------------------------------------------------------
# Search Existing Folders
# -----------------------------------------------------------------------------

# Search Subjects / Sessions
# -----------------------------------------------------------------------------


def search_sub_or_ses_level(
    cfg: Configs,
    base_folder: Path,
    local_or_central: str,
    sub: Optional[str] = None,
    ses: Optional[str] = None,
    search_str: str = "*",
    verbose: bool = True,
) -> Tuple[List[str], List[str]]:
    """
    Search project folder at the subject or session level.
    Only returns folders

    Parameters
    ----------

    cfg : datashuttle project cfg. Currently, this is used
        as a holder for  ssh configs to avoid too many
        arguments, but this is not nice and breaks the
        general rule that these functions should operate
        project-agnostic.

    local_or_central : search in local or central project

    sub : either a subject name (string) or None. If None, the search
        is performed at the top_level_folder level

    ses : either a session name (string) or None, This must not
        be a session name if sub is None. If provided (with sub)
        then the session folder is searched

    str : glob-format search string to search at the
        folder level.

    verbose : If `True`, if a search folder cannot be found, a message
              will be printed with the un-found path.
    """
    if ses and not sub:
        utils.log_and_raise_error(
            "cannot pass session to "
            "search_sub_or_ses_level() without subject"
        )

    if sub:
        base_folder = base_folder / sub

    if ses:
        base_folder = base_folder / ses

    all_folder_names, all_filenames = search_for_folders(
        cfg,
        base_folder,
        local_or_central,
        search_str,
        verbose,
    )

    return all_folder_names, all_filenames


def search_data_folders_sub_or_ses_level(
    cfg: Configs,
    base_folder: Path,
    local_or_central: str,
    sub: str,
    ses: Optional[str] = None,
) -> zip:
    """
    Search  a subject or session folder specifically
    for datatypes. First searches for all folders / files
    in the folder, and then returns any folders that
    match datatype name.

    see folders.search_sub_or_ses_level() for full
    parameters list.

    Returns
    -------
    Find the datatype files and return in
    a format that mirrors dict.items()
    """
    search_results = search_sub_or_ses_level(
        cfg, base_folder, local_or_central, sub, ses
    )[0]

    data_folders = process_glob_to_find_datatype_folders(
        search_results,
        cfg.datatype_folders,
    )
    return data_folders


def search_for_wildcards(
    cfg: Configs,
    base_folder: Path,
    local_or_central: str,
    all_names: List[str],
    sub: Optional[str] = None,
) -> List[str]:
    """
    Handle wildcard flag in upload or download.

    All names in name are searched for @*@ string, and replaced
    with single * for glob syntax. If sub is passed, it is
    assumes all_names is ses_names and the sub folder is searched
    for ses_names matching the name including wildcard. Otherwise,
    if sub is None it is assumed all_names are sub names and
    the level above is searched.

    Outputs a new list of names including all original names
    but where @*@-containing names have been replaced with
    search results.

    Parameters
    ----------

    project : initialised datashuttle project

    base_folder : folder to search for wildcards in

    local_or_central : "local" or "central" project path to
        search in

    all_names : list of subject or session names that
        may or may not include the wildcard flag. If sub (below)
        is passed, it is assumed these are session names. Otherwise,
        it is assumed these are subject names.

    sub : optional subject to search for sessions in. If not provided,
        will search for subjects rather than sessions.

    """
    new_all_names = []
    for name in all_names:
        if canonical_tags.tags("*") in name:
            name = name.replace(canonical_tags.tags("*"), "*")

            if sub:
                matching_names = search_sub_or_ses_level(
                    cfg, base_folder, local_or_central, sub, search_str=name
                )[0]
            else:
                matching_names = search_sub_or_ses_level(
                    cfg, base_folder, local_or_central, search_str=name
                )[0]

            new_all_names += matching_names
        else:
            new_all_names += [name]

    new_all_names = list(
        set(new_all_names)
    )  # remove duplicate names in case of wildcard overlap

    return new_all_names


def get_all_sub_and_ses_names(
    cfg: Configs,
) -> Dict:
    """
    Get a list of every subject and session name in the
    local and central project folders. Local and central names are combined
    into a single list, separately for subject and sessions.

    Note this only finds local sub and ses names on this
    machine. Other local machines are not searched.
    """
    sub_folder_names = get_local_and_central_sub_or_ses_names(
        cfg, None, "sub-*"
    )

    all_sub_folder_names = (
        sub_folder_names["local"] + sub_folder_names["central"]
    )

    all_ses_folder_names = []
    for sub in all_sub_folder_names:
        ses_folder_names = get_local_and_central_sub_or_ses_names(
            cfg, sub, "ses-*"
        )

        all_ses_folder_names.extend(
            ses_folder_names["local"] + ses_folder_names["central"]
        )

    return {"sub": all_sub_folder_names, "ses": all_ses_folder_names}


# Search Data Types
# -----------------------------------------------------------------------------


def process_glob_to_find_datatype_folders(
    folder_names: list,
    datatype_folders: dict,
) -> zip:
    """
    Process the results of glob on a sub or session level,
    which could contain any kind of folder / file.

    see project.search_sub_or_ses_level() for inputs.

    Returns
    -------
    Find the datatype files and return in
    a format that mirrors dict.items()
    """
    ses_folder_keys = []
    ses_folder_values = []
    for name in folder_names:
        datatype_key = [
            key
            for key, value in datatype_folders.items()
            if value.name == name
        ]

        if datatype_key:
            ses_folder_keys.append(datatype_key[0])
            ses_folder_values.append(datatype_folders[datatype_key[0]])

    return zip(ses_folder_keys, ses_folder_values)


# Low level search functions
# -----------------------------------------------------------------------------


def search_for_folders(  # TODO: change name
    cfg: Configs,
    search_path: Path,
    local_or_central: str,
    search_prefix: str,
    verbose: bool = True,
) -> Tuple[List[Any], List[Any]]:
    """
    Wrapper to determine the method used to search for search
    prefix folders in the search path.

    Parameters
    ----------

    local_or_central : "local" or "central"
    search_path : full filepath to search in
    search_prefix : file / folder name to search (e.g. "sub-*")
    verbose : If `True`, when a search folder cannot be found, a message
          will be printed with the missing path.
    """
    if local_or_central == "central" and cfg["connection_method"] == "ssh":
        all_folder_names, all_filenames = ssh.search_ssh_central_for_folders(
            search_path,
            search_prefix,
            cfg,
            verbose,
        )
    else:
        if not search_path.exists():
            if verbose:
                utils.log_and_message(
                    f"No file found at {search_path.as_posix()}"
                )
            return [], []

        all_folder_names, all_filenames = search_filesystem_path_for_folders(
            search_path / search_prefix
        )
    return all_folder_names, all_filenames


def search_filesystem_path_for_folders(
    search_path_with_prefix: Path,
) -> Tuple[List[str], List[str]]:
    """
    Use glob to search the full search path (including prefix) with glob.
    Files are filtered out of results, returning folders only.
    """
    all_folder_names = []
    all_filenames = []
    for file_or_folder in glob.glob(search_path_with_prefix.as_posix()):
        if os.path.isdir(file_or_folder):
            all_folder_names.append(os.path.basename(file_or_folder))
        else:
            all_filenames.append(os.path.basename(file_or_folder))

    return all_folder_names, all_filenames


def get_local_and_central_sub_or_ses_names(
    cfg: Configs, sub: Optional[str], search_str: str
) -> Dict:
    """
    If sub is None, the top-level level folder will be searched (i.e. for subjects).
    The search string "sub-*" is suggested in this case. Otherwise, the subject,
    level folder for the specified subject will be searched. The search_str
    "ses-*" is suggested in this case.

    Note `verbose` argument of `search_sub_or_ses_level()` is set to `False`,
    as session folders for local subjects that are not yet on central
    will be searched for on central, showing a confusing 'folder not found'
    message.
    """

    # Search local and central for folders that begin with "sub-*"
    local_foldernames, _ = search_sub_or_ses_level(
        cfg,
        cfg.get_base_folder("local"),
        "local",
        sub=sub,
        search_str=search_str,
        verbose=False,
    )
    central_foldernames, _ = search_sub_or_ses_level(
        cfg,
        cfg.get_base_folder("central"),
        "central",
        sub,
        search_str=search_str,
        verbose=False,
    )
    return {"local": local_foldernames, "central": central_foldernames}


def get_next_sub_or_ses_number(
    cfg: Configs, sub: Optional[str], search_str: str
) -> Tuple[int, int]:
    """
    Suggest the next available subject or session number. This function will
    search the local repository, and the central repository, for all subject
    or session folders (subject or session depending on inputs).
    It will take the union of all folder names, find the relevant key-value
    pair values, and return the maximum value + 1 as the new number.
    A warning will be shown if the existing sub / session numbers are not
    consecutive.


    Parameters
    ----------
    cfg : datashuttle configs class
    sub : subject name to search within if searching for sessions, otherwise None
          to search for subjects
    search_str : the string to search for within the top-level or subject-levle
                 folder ("sub-*") or ("ses-*") are suggested, respectively.
    Returns
    -------
    suggested_new_num : the new suggested sub / ses number.
    latest_existing_num : the latest sub / ses number that currently
                          exists in the project.
    """

    if sub:
        bids_key = "ses"
    else:
        bids_key = "sub"

    folder_names = get_local_and_central_sub_or_ses_names(
        cfg,
        sub,
        search_str,
    )

    # Convert subject values to a list of increasing-by-1 integers
    all_folders = list(set(folder_names["local"] + folder_names["central"]))

    if len(all_folders) == 0:
        utils.raise_error("No folders found. Cannot suggest the next number.")

    all_value_nums = utils.get_values_from_bids_formatted_name(
        all_folders,
        bids_key,
        return_as_int=True,
        sort=True,
    )

    if not utils.integers_are_consecutive(all_value_nums):
        warnings.warn(
            f"A subject number has been skipped, "
            f"currently used subject numbers are: {all_value_nums}"
        )

    # calculate next sub number
    latest_existing_num = max(all_value_nums)
    suggested_new_num = latest_existing_num + 1

    return suggested_new_num, latest_existing_num


def get_existing_project_paths_and_names() -> Tuple[List[str], List[Path]]:
    """
    Return full path and names of datashuttle projects on
    this local machine. A project is determined by a project
    folder in the home / .datashuttle folder that contains a
    config.yaml file.
    """
    datashuttle_path = canonical_folders.get_datashuttle_path()

    all_folders, _ = folders.search_filesystem_path_for_folders(
        datashuttle_path / "*"
    )

    existing_project_paths = []
    existing_project_names = []
    for folder_name in all_folders:
        config_file = list(
            (datashuttle_path / folder_name).glob("config.yaml")
        )

        if len(config_file) > 1:
            utils.raise_error(
                f"There are two config files in project"
                f"{folder_name} at path {datashuttle_path}. There "
                f"should only ever be one config per project. "
            )
        elif len(config_file) == 1:
            existing_project_paths.append(datashuttle_path / folder_name)
            existing_project_names.append(folder_name)

    return existing_project_names, existing_project_paths
