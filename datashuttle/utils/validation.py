from __future__ import annotations

import re
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple, Union

if TYPE_CHECKING:
    from datashuttle.configs.config_class import Configs
    from datashuttle.utils.custom_types import (
        DisplayMode,
        Prefix,
        TopLevelFolder,
    )

from itertools import chain

from datashuttle.configs import canonical_folders
from datashuttle.utils import formatting, getters, utils
from datashuttle.utils.custom_exceptions import NeuroBlueprintError

# -----------------------------------------------------------------------------
# Checking a standalone list of names
# -----------------------------------------------------------------------------


def validate_list_of_names(
    names_list: List[str],
    prefix: Prefix,
    display_mode: DisplayMode = "error",
    check_duplicates: bool = True,
    name_templates: Optional[Dict] = None,
    log: bool = True,
) -> None:
    """
    Validate a list of subject or session names, ensuring
    they are formatted as per NeuroBlueprint.

    Parameters
    ----------

    names_list : List[str]
        A list of NeuroBlueprint-formatted names to validate

    prefix: Prefix
        Whether these are subject (sub) or session (ses) level names

    display_mode: DisplayMode
        If an invalid case is found, whether to raise error or warning

    check_duplicates : bool
        The function `duplicated_prefix_values()` performs a quick check
        for duplicate sub / ses values in the names. However, this will
        raise on any duplicate, see `new_name_duplicates_existing()`
        for a more flexible function used during new folder creation.

    log: bool
        If `True`, output will also be logged to "datashuttle" logger.

    Notes
    ------
    Each subfunction called in this function loops over the entire
    list of names. This is done in this way so each subfunction
    is modular. However for large projects this may become slow.
    """
    if len(names_list) == 0:
        return

    tests_to_run = [
        lambda: name_begins_with_bad_key(names_list, prefix),
        lambda: names_include_special_characters(names_list),
        lambda: dashes_and_underscore_alternate_incorrectly(names_list),
        lambda: value_lengths_are_inconsistent(names_list, prefix),
        lambda: names_dont_match_templates(names_list, prefix, name_templates),
    ]
    if check_duplicates:
        tests_to_run += [lambda: duplicated_prefix_values(names_list, prefix)]

    for test in tests_to_run:
        failed, message = test()
        if failed:
            raise_display_mode(message, display_mode, log)


def names_dont_match_templates(
    names_list: List[str],
    prefix: Prefix,
    name_templates: Optional[Dict] = None,
) -> Tuple[bool, str]:
    """
    Test a list of subject or session names against
    the respective `name_templates`, a regexp template.

    If checking `name_templates` is on, an invalid result will be given if the
    name does not re.fullmatch the regexp.
    """
    if name_templates is None:
        return False, "No `names_template` dictionary passed."

    if name_templates["on"] is False:
        return (
            False,
            "Names templates is set to off and will not be checked.",
        )

    regexp = name_templates[prefix]

    if regexp is None:
        return False, f"No template set for prefix: {prefix}"

    regexp = replace_tags_in_regexp(regexp)

    bad_names = []
    for name in names_list:
        if not re.fullmatch(regexp, name):
            bad_names.append(name)

    if bad_names:
        do_or_does = "does" if len(bad_names) == 1 else "do"

        return (
            True,
            f"The {get_names_format(bad_names)} "
            f"{do_or_does} not match the template: {regexp}",
        )

    return False, ""


def replace_tags_in_regexp(regexp: str) -> str:
    """
    Before validation, all tags in the names are converted to
    their final values (e.g. @DATE@ -> _date-<date>). We also want to
    allow template to be formatted like `sub-\d\d_@DATE@` as it
    is convenient for auto-completion in the TUI.

    Therefore we must replace the tags in the regexp with their
    actual regexp equivalent before comparison.
    Note `replace_date_time_tags_in_name()` operates in place on a list.
    """
    regexp_list = [regexp]
    date_regexp = "\d\d\d\d\d\d\d\d"
    time_regexp = "\d\d\d\d\d\d"
    formatting.replace_date_time_tags_in_name(
        regexp_list,
        datetime_with_key=formatting.format_datetime(date_regexp, time_regexp),
        date_with_key=formatting.format_date(date_regexp),
        time_with_key=formatting.format_time(time_regexp),
    )
    return regexp_list[0]


def get_names_format(bad_names):
    """
    A convenience function to properly format error messages
    depending on whether there is just 1, or multiple bad names.
    """
    assert len(bad_names) != 0, "`bad_names` should not be empty."
    if len(bad_names) == 1:
        name_str_format = "name"
        bad_names_format = bad_names[0]
    else:
        name_str_format = "names"
        bad_names_format = bad_names

    return f"{name_str_format}: {bad_names_format}"


def name_begins_with_bad_key(
    names_list: List[str], prefix: Prefix
) -> Tuple[bool, str]:
    """
    Check that a list of NeuroBlueprint names begin
    with the required subject or session.

    Returns `True` if an invalid name was found, along
     with a message detailing the error.
    """
    bad_names = []
    for name in names_list:
        if name[:4] != f"{prefix}-":
            bad_names.append(name)

    if bad_names:
        message = (
            f"The {get_names_format(bad_names)} "
            f"do not begin with the required prefix: {prefix}"
        )
        return True, message

    return False, ""


def names_include_special_characters(
    names_list: List[str],
) -> Tuple[bool, str]:
    """
    Check that a list of NeuroBlueprint formatted
    names do not contain special characters (i.e. characters
    that are not integers, letters, dash or underscore).

    Returns `True` if an invalid name was found, along
    with a message detailing the error.
    """
    bad_names = []
    for name in names_list:
        if name_has_special_character(name):
            bad_names.append(name)

    if bad_names:
        return (
            True,
            f"The name: {get_names_format(bad_names)}, contains characters "
            f"which are not alphanumeric, dash or underscore.",
        )
    return False, ""


def name_has_special_character(name: str) -> bool:
    return not re.match("^[A-Za-z0-9_-]*$", name)


def dashes_and_underscore_alternate_incorrectly(
    names_list: List[str],
) -> Tuple[bool, str]:
    """
    Check a list of NeuroBlueprint formatted names
    have the "-" and "-" ordered correctly. Names should be
    key-value pairs separated by underscores e.g.
    sub-001_ses-001.

    Returns `True` if an invalid name was found, along
    with a message detailing the error.
    """
    bad_names = []
    for name in names_list:
        discrim = {"-": 1, "_": -1}

        dashes_underscores = [
            discrim[ele] for ele in name if ele in ["-", "_"]
        ]

        underscore_dash_not_interleaved = any(
            [ele == 0 for ele in utils.diff(dashes_underscores)]
        )

        if (
            (dashes_underscores[0] != 1)
            or underscore_dash_not_interleaved
            or (name[-1] in discrim.keys())
        ):
            bad_names.append(name)

    if bad_names:
        message = (
            f"Problem with {get_names_format(bad_names)}. Names "
            f"must consist of key-value pairs separated by underscores."
            f"e.g. 'sub-001_ses-01_date-20230516"
        )
        return True, message

    return False, ""


def value_lengths_are_inconsistent(
    names_list: List[str],
    prefix: Prefix,
) -> Tuple[bool, str]:
    """
    Given a list of NeuroBlueprint-formatted subject or session
    names, determine if there are inconsistent value lengths for
    the sub or ses key.

    Returns `True` if an invalid name was found, along
    with a message detailing the error.
    """
    prefix_values = utils.get_values_from_bids_formatted_name(
        names_list, prefix, return_as_int=False
    )

    value_len = [len(value) for value in prefix_values]

    inconsistent_value_len = value_len != [] and not utils.all_identical(
        value_len
    )

    if inconsistent_value_len:
        message = (
            f"Inconsistent value lengths for the key {prefix} were "
            f"found. Ensure the number of digits for the {prefix} value "
            f"are the same and prefixed with leading zeros if required."
        )
        return True, message

    return False, ""


def duplicated_prefix_values(
    names_list: List[str], prefix: Prefix
) -> Tuple[bool, str]:
    """
    Check a list of subject or session names for duplicate
    ids (e.g. not allowing ["sub-001", "sub-001_@DATE@"])

    This is a quick function however it will raise if two
    exact duplicates are in the list (e.g. ["sub-001", "sub-001"]).
    This may happen (e.g. if the same subject is on local and
    central). See `new_name_duplicates_existing()` for a
    function that permits exact matches.

    Returns `True` if an invalid name was found, along
    with a message detailing the error.
    """
    int_values = utils.get_values_from_bids_formatted_name(
        names_list, prefix, return_as_int=True
    )

    has_duplicate_ids = not utils.all_unique(int_values)

    if has_duplicate_ids:
        message = (
            f"{prefix} names must all have unique integer ids"
            f" after the {prefix} prefix."
        )
        return True, message

    return False, ""


def raise_display_mode(
    message: str, display_mode: DisplayMode, log: bool
) -> None:
    """
    Given an error message, raise an error or warning, and log or
    do not log, depending on the passed arguments.
    """
    if display_mode == "error":
        utils.log_and_raise_error(message, NeuroBlueprintError)

    elif display_mode == "warn":
        utils.warn(message, log=log)

    elif display_mode == "print":
        if log:
            utils.log_and_message(message)
        else:
            utils.print_message_to_user(message)
    else:
        raise ValueError(
            "`display_mode` must be either 'error', 'warn', 'print'."
        )


# -----------------------------------------------------------------------------
# Validate Entire Project
# -----------------------------------------------------------------------------


def validate_project(
    cfg: Configs,
    top_level_folder: TopLevelFolder,
    local_only: bool = False,
    display_mode: DisplayMode = "error",
    log: bool = True,
    name_templates: Optional[Dict] = None,
) -> None:
    """
    Validate all subject and session folders within a project.

    A list of all subjects and sessions per-subject is retrieved from
    the project. We want to check all names at a certain level (e.g.
    all subject filenames contain the same number of "sub-" value digits).
    For duplicate checks, exact duplicates are allowed (for example
    subjects will be duplicated across `local_path` and `central_path`)
    but subject / sessions that share the same value but are otherwise
    different are not allowed.

    Parameters
    -----------

    cfg : Configs
        datashuttle Configs class.

    top_level_folder:  TopLevelFolder
        The top level folder to validate.

    local_only : bool
        If `True`, only project folders in the `local_path` will
        be validated. Otherwise, project folders in both the `local_path`
        and `central_path` will be validated.

    display_mode : DisplayMode
        Determine whether error or warning is raised.

    log : bool
        If `True`, errors or warnings are logged to "datashuttle" logger.
    """
    folder_names = getters.get_all_sub_and_ses_names(
        cfg, top_level_folder, local_only
    )

    # Check subjects
    sub_names = folder_names["sub"]

    validate_list_of_names(
        sub_names,
        prefix="sub",
        display_mode=display_mode,
        log=log,
        check_duplicates=False,
        name_templates=name_templates,
    )

    for sub in sub_names:
        failed, message = new_name_duplicates_existing(sub, sub_names, "sub")
        if failed:
            raise_display_mode(message, display_mode, log)

    # Check sessions
    all_ses_names = list(chain(*folder_names["ses"].values()))

    validate_list_of_names(
        all_ses_names,
        "ses",
        check_duplicates=False,
        display_mode=display_mode,
        log=log,
    )

    for ses_names in folder_names["ses"].values():
        for ses in ses_names:
            failed, message = new_name_duplicates_existing(
                ses, ses_names, "ses"
            )
            if failed:
                raise_display_mode(message, display_mode, log)


def validate_names_against_project(
    cfg: Configs,
    top_level_folder: TopLevelFolder,
    sub_names: List[str],
    ses_names: Optional[List[str]] = None,
    local_only: bool = False,
    display_mode: DisplayMode = "error",
    log: bool = True,
    name_templates: Optional[Dict] = None,
) -> None:
    """
    Given a list of subject and (optionally) session names,
    check that these names are formatted consistently with the
    rest of the project. Unfortunately this function has become
    quite complex due to the need to only validate the passed
    list of subject / session names while ignoring validation errors
    that may already exist in the project.

    The passed list of names is first validated in `validate_list_of_names()`
    without reference to the existing project.

    Next, checks for inconsistent length of sub or ses values are checked.
    This cannot be run if there are inconsistent values within the project
    itself, which will throw an error in this case. Only valid sub / ses
    names within the project are checked.

    Finally, checks for duplicate subjects / sessions are performed. For subjects,
    duplicates are checked for project-wide. For sessions, duplicates are
    checked for within the corresponding folders. This assumes that
    the passed `ses_names` will be created in all passed `sub_names`.

    Parameters
    ----------

    cfg : Configs
        datashuttle Configs class.

    top_level_folder :  TopLevelFolder
        The top level folder to validate

    sub_names : List[str]
        A list of subject-level names to validate against the
        subject names that exist in the project.

    ses_names : List[str]
        A list of session-level names to validate against the
        session names that exist in the project. Note that
        duplicate checks will only be performed for sessions within
        the passed `sub_names`.

    local_only : bool
        If `True`, only project folders in the `local_path` will
        be validated against. Otherwise, project folders in both the
        `local_path` and `central_path` will be validated against.

    display_mode : DisplayMode
        Determine whether error or warning is raised.

    log : bool
        If `True`, errors or warnings are logged to "datashuttle" logger.

    TODO
    ----
    This function is now quite confusing, and in general the validation
    needs optimisation are there are frequent looping over the same
    list under different circumstances. See issue #355
    """
    folder_names = getters.get_all_sub_and_ses_names(
        cfg, top_level_folder, local_only
    )

    # Check subjects
    if folder_names["sub"]:
        validate_list_of_names(
            sub_names,
            prefix="sub",
            check_duplicates=True,
            display_mode=display_mode,
            name_templates=name_templates,
        )

        valid_sub_in_project = strip_invalid_names(folder_names["sub"], "sub")

        check_sub_names_value_length_are_consistent_with_project(
            sub_names, valid_sub_in_project, display_mode, log
        )

        for new_sub in sub_names:

            failed, message = new_name_duplicates_existing(
                new_sub, valid_sub_in_project, "sub"
            )
            if failed:
                raise_display_mode(message, display_mode, log)

    # Check sessions
    if folder_names["sub"] and ses_names is not None:

        validate_list_of_names(
            ses_names,
            "ses",
            check_duplicates=True,
            display_mode=display_mode,
        )

        # For all the subjects, check that the ses_names are valid
        # for all sessions currently within those subjects.
        for new_sub in sub_names:
            if new_sub in folder_names["ses"]:

                valid_ses_in_sub = strip_invalid_names(
                    folder_names["ses"][new_sub], "ses"
                )

                check_ses_names_value_length_are_consistent_with_project(
                    ses_names, valid_ses_in_sub, new_sub, display_mode, log
                )

                for new_ses in ses_names:
                    failed, message = new_name_duplicates_existing(
                        new_ses, valid_ses_in_sub, "ses"
                    )
                    if failed:
                        raise_display_mode(message, display_mode, log)


def check_sub_names_value_length_are_consistent_with_project(
    sub_names: List[str],
    valid_sub_in_project: List[str],
    display_mode: DisplayMode,
    log: bool,
) -> None:
    """
    Given a list of names we are validating, and a list of
    all the other names that current exist in the project, check
    the list of names has consistent value length with all the
    other names in the project.

    Note this will throw an error if the project odes not have
    consistent value length as this check will not be possible
    otherwise.
    """
    if value_lengths_are_inconsistent(valid_sub_in_project, "sub")[0]:
        raise_display_mode(
            "Cannot check names for inconsistent value lengths "
            "because the subject value lengths are not consistent "
            "across the project.",
            display_mode,
            log,
        )
    else:
        failed, message = value_lengths_are_inconsistent(
            sub_names + valid_sub_in_project, "sub"
        )
        if failed:
            raise_display_mode(message, display_mode, log)


def check_ses_names_value_length_are_consistent_with_project(
    ses_names: List[str],
    valid_ses_in_sub: List[str],
    sub_name: str,
    display_mode: DisplayMode,
    log: bool,
) -> None:
    """
    See check_sub_names_value_length_are_consistent_with_project(),
    this performs the same function for session. Potential to merge
    with that function, just some minor annoying differences.
    """
    if value_lengths_are_inconsistent(valid_ses_in_sub, "ses")[0]:
        raise_display_mode(
            f"Cannot check names for inconsistent value lengths "
            f"because the session value lengths for subject "
            f"{sub_name} are not consistent.",
            display_mode,
            log,
        )
    else:
        failed, message = value_lengths_are_inconsistent(
            ses_names + valid_ses_in_sub, "ses"
        )
        if failed:
            raise_display_mode(message, display_mode, log)


def strip_invalid_names(all_names: List[str], prefix: Prefix) -> List[str]:
    """ """
    new_list = []
    for name in all_names:
        try:
            utils.get_values_from_bids_formatted_name(
                [name], prefix, return_as_int=True
            )[0]
        except NeuroBlueprintError:
            continue
        new_list.append(name)

    return new_list


def new_name_duplicates_existing(
    new_name: str, existing_names: List[str], prefix: Prefix
) -> Tuple[bool, str]:
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
    # Make a list of matches between `new_name` and any in `existing_names`
    new_name_id = utils.get_values_from_bids_formatted_name(
        [new_name], prefix, return_as_int=True
    )[0]

    for exist_name in existing_names:

        exist_name_id = utils.get_values_from_bids_formatted_name(
            [exist_name], prefix, return_as_int=True
        )[0]

        if exist_name_id == new_name_id:
            if new_name != exist_name:
                message = (
                    f"A {prefix} already exists with "
                    f"the same {prefix} id as {new_name}. "
                    f"The existing folder is {exist_name}."
                )
                return True, message

    return False, ""


# -----------------------------------------------------------------------------
# Data types
# -----------------------------------------------------------------------------


def datatypes_are_invalid(
    datatype: Union[List[str], str], allow_all: bool = False
) -> Tuple[bool, str]:
    """
    Check a datatype of list of datatypes is a valid
    NeuroBlueprint datatype.

    Returns `True` if an invalid name was found, along
    with a message detailing the error.
    """
    datatype_folders = canonical_folders.get_datatype_folders()

    if isinstance(datatype, str):
        datatype = [datatype]

    valid_keys = list(datatype_folders.keys())
    if allow_all:
        valid_keys += ["all"]

    bad_datatypes = []
    for dt in datatype:
        if dt not in valid_keys:
            bad_datatypes.append(dt)

    if bad_datatypes:
        or_all = " or 'all'" if allow_all else ""
        message = (
            f"datatypes: '{bad_datatypes}' are not valid. Must be one of"
            f" {list(datatype_folders.keys())}{or_all}. "
            f"No folders were made."
        )
        return True, message

    return False, ""
