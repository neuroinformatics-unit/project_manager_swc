from __future__ import annotations

from typing import TYPE_CHECKING, List, Literal, Optional, Union

if TYPE_CHECKING:
    from datashuttle.configs.config_class import Configs

from itertools import chain

from ..configs import canonical_folders
from . import folders, utils

# -----------------------------------------------------------------------------
# Checking a standalone list of names
# -----------------------------------------------------------------------------


def validate_list_of_names(
    names_list: List[str], prefix: Literal["sub", "ses"], check_duplicates=True
) -> None:
    """
    Validate a list of subject or session names, ensuring
    they are formatted as per NeuroBlueprint.

    We cannot validate names with "@*@" tags in.
    """
    if len(names_list) == 0:
        return

    check_all_names_begin_with_prefix(names_list, prefix)

    check_list_of_names_for_spaces(names_list, prefix)

    check_dashes_and_underscore_alternate_correctly(names_list)

    check_names_for_inconsistent_value_lengths(
        names_list, prefix, raise_error=True
    )

    if check_duplicates:
        quick_check_for_duplicate_ids(names_list, prefix)


def check_all_names_begin_with_prefix(
    names_list: List[str], prefix: Literal["sub", "ses"]
) -> None:  # TODO: test
    """ """
    begin_with_prefix = all([name[:4] == f"{prefix}-" for name in names_list])

    if not begin_with_prefix:
        utils.log_and_raise_error(
            f"Not all names in the list: {names_list} "
            f"begin with the required prefix: {prefix}"
        )


def check_list_of_names_for_spaces(  # TODO: test
    names_list: List[str], prefix: Literal["sub", "ses"]
) -> None:
    """ """
    if any([" " in ele for ele in names_list]):
        utils.log_and_raise_error(f"{prefix} names cannot include spaces.")


def check_dashes_and_underscore_alternate_correctly(
    names_list: List[str],
) -> None:
    """ """
    for name in names_list:
        discrim = {"-": 1, "_": -1}
        dashes_underscores = [
            discrim[ele] for ele in name if ele in ["-", "_"]
        ]

        if dashes_underscores[0] != 1:
            utils.log_and_raise_error(
                "The first delimiter of 'sub' or 'ses' "
                "must be dash not underscore e.g. sub-001."
            )

        if any([ele == 0 for ele in utils.diff(dashes_underscores)]):
            utils.log_and_raise_error(
                "Subject and session names must contain alternating dashes "
                "and underscores (used for separating key-value pairs)."
            )


def check_names_for_inconsistent_value_lengths(
    names_list: List[str],
    prefix: Literal["sub", "ses"],
    raise_error=False,
) -> bool:
    """
    Given a list of NeuroBlueprint-formatted subject or session
    names, determine if there are inconsistent value lengths for
    the sub or ses key.
    """
    prefix_values = utils.get_values_from_bids_formatted_name(
        names_list, prefix, return_as_int=False
    )

    value_len = [len(value) for value in prefix_values]

    if value_len != [] and not all_identical(value_len):
        inconsistent_lengths = True
    else:
        inconsistent_lengths = False

    if raise_error and inconsistent_lengths:
        utils.log_and_raise_error(
            f"Inconsistent value lengths for the key {prefix} were found. "
            f"Ensure the number of digits for the {prefix} value are the same "
            f"and prefixed with leading zeros if required."
        )

    return inconsistent_lengths


def quick_check_for_duplicate_ids(
    names_list: List[str], prefix: Literal["sub", "ses"]
) -> None:
    """
    Check a list of subject or session names for duplicate
    ids (e.g. not allowing ["sub-001", "sub-001_@DATE@"])
    """
    int_values = utils.get_values_from_bids_formatted_name(
        names_list, prefix, return_as_int=True
    )
    if not all_unique(int_values):
        utils.log_and_raise_error(
            f"{prefix} names must all have unique integer ids"
            f" after the {prefix} prefix."
        )


# -----------------------------------------------------------------------------
# Data types
# -----------------------------------------------------------------------------


def check_datatype_is_valid(
    datatype: Union[List[str], str], error_on_fail: bool, allow_all=False
) -> bool:
    """
    Check the passed datatype is valid (must be a key on
    self.ses_folders e.g. "behav", or "all")
    """
    datatype_folders = canonical_folders.get_datatype_folders()

    if isinstance(datatype, str):
        datatype = [datatype]

    valid_keys = list(datatype_folders.keys())
    if allow_all:
        valid_keys += ["all"]

    is_valid = all([dt in valid_keys for dt in datatype])

    if error_on_fail and not is_valid:
        utils.log_and_raise_error(
            f"datatype: '{datatype}' "
            f"is not valid. Must be one of"
            f" {list(datatype_folders.keys())}. or 'all'"
            f" No folders were made."
        )

    return is_valid


# -----------------------------------------------------------------------------
# More integrated : Searching for Folders (then working on a list)
# -----------------------------------------------------------------------------


def validate_project(cfg, local_only=False):  # base_folder
    """"""
    folder_names = folders.get_all_sub_and_ses_names(cfg, local_only)

    sub_names = folder_names["sub"]

    validate_list_of_names(sub_names, prefix="sub")

    all_ses_names = list(chain(*folder_names["ses"].values()))

    validate_list_of_names(all_ses_names, "ses", check_duplicates=False)

    for ses_names in folder_names["ses"].values():
        quick_check_for_duplicate_ids(ses_names, "ses")


def validate_names_against_project(
    cfg: Configs,
    sub_names: List[str],
    ses_names: Optional[List[str]] = None,
    local_only=False,
) -> None:
    """
    This does not support subject-spceific checking, this needs to be handled a level up
    i.e. pass 1 sub, and it's sessions. It is presumed the sessions
    are for the subjects passed for the duplicate checks
    """
    folder_names = folders.get_all_sub_and_ses_names(cfg, local_only)

    if folder_names["sub"]:  # warn otherwise?
        validate_list_of_names(
            sub_names + folder_names["sub"],
            prefix="sub",
            check_duplicates=False,
        )

        for new_sub in sub_names:
            check_new_name_does_not_duplicate_existing(
                new_sub, folder_names["sub"], "sub"
            )

        if ses_names is not None:
            all_ses_names = list(set(chain(*folder_names["ses"].values())))

            validate_list_of_names(
                all_ses_names + ses_names, "ses", check_duplicates=False
            )

            # TODO: doc this, confusing.
            for new_sub in sub_names:
                if new_sub in folder_names["ses"]:
                    for new_ses in ses_names:
                        check_new_name_does_not_duplicate_existing(
                            new_ses, folder_names["ses"][new_sub], "ses"
                        )


def check_new_name_does_not_duplicate_existing(
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
    # Make a list of matches between `new_name` and any in `existing_names`
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

    # If more than one match is found, there is definitely a duplicate
    if len(matched_existing_names) > 1:
        utils.log_and_raise_error(
            f"Cannot make folders. Multiple {prefix} ids "
            f"exist: {matched_existing_names}. This should"
            f"never happen. Check the {prefix} ids and ensure unique {prefix} "
            f"ids (e.g. sub-001) appear only once."
        )

    # If exactly one match is found, it should match exactly.
    if len(matched_existing_names) == 1:
        if new_name != matched_existing_names[0]:
            utils.log_and_raise_error(
                f"Cannot make folders. A {prefix} already exists "
                f"with the same {prefix} id as {new_name}. "
                f"The existing folder is {matched_existing_names[0]}."
            )


# -----------------------------------------------------------------------------
# Utils (TODO: move to utils?)
# -----------------------------------------------------------------------------


def all_unique(list_: List) -> bool:
    return len(list_) == len(set(list_))


def all_identical(list_: List) -> bool:
    return len(set(list_)) == 1
