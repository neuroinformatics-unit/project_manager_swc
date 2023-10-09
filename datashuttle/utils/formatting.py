from __future__ import annotations

import datetime
import re
import warnings
from itertools import compress
from typing import TYPE_CHECKING, Any, Dict, List, Literal, Union

from datashuttle.configs.canonical_folders import get_keys_that_we_cant_format
from datashuttle.configs.canonical_tags import tags

if TYPE_CHECKING:
    from datashuttle.configs.config_class import Configs

from . import folders, utils

# --------------------------------------------------------------------------------------------------------------------
# Format Sub / Ses Names
# --------------------------------------------------------------------------------------------------------------------


def check_and_format_names(
    names: Union[list, str],
    prefix: Literal["sub", "ses"],
) -> List[str]:
    """
    Format a list of subject or session names, e.g.
    by ensuring all have sub- or ses- prefix, checking
    for tags, that names do not include spaces and that
    there are not duplicates.

    Note that as we might have canonical keys e.g. "all_sub"
    or certain tags e.g. "@*@" we cannot perform validation on
    these keys as they intrinsically break the NeuroBlueprint rules.
    However, in practice this is not an issue because you won't make a
    folder with "@*@" in it anyway, this is strictly for searching
    during upload / download. see canonical_folders.get_keys_that_we_cant_format()
    for more information.

    Parameters
    ----------

    names: str or list containing sub or ses names
                  (e.g. to make folders)

    prefix: "sub" or "ses" - this defines the prefix checks.
    """
    if isinstance(names, str):
        names = [names]

    names_to_check, reserved_keywords = [], []
    for name in names:
        if name in get_keys_that_we_cant_format():
            reserved_keywords.append(name)
        else:
            names_to_check.append(name)

    formatted_names = format_names(names_to_check, prefix)

    validate_names(formatted_names, prefix)

    return formatted_names + reserved_keywords


def validate_names(all_names, prefix):
    """
    Validate a list of subject or session names, ensuring
    they are formatted as per NeuroBlueprint.
    """
    if len(all_names) != len(set(all_names)):
        utils.log_and_raise_error(
            "Subject and session names must all be unique (i.e. there are no"
            " duplicates in list input)."
        )
    if len(names_to_check) == 0:
        return

    check_dashes_and_underscore_alternate_correctly(all_names)

    check_names_for_duplicate_ids_and_inconsistent_leading_zeros(
        names_to_check, prefix
    )

def format_names(names: List, prefix: Literal["sub", "ses"]) -> List[str]:
    """
    Check a single or list of input session or subject names.

    First check the type is correct, next prepend the prefix
    sub- or ses- to entries that do not have the relevant prefix.
    Finally, check for duplicates and replace any tags
    with required inputs e.g. date, time

    Parameters
    -----------
    names: str or list containing sub or ses names (e.g. to make folders)

    prefix: "sub" or "ses" - this defines the prefix checks.
    """
    assert prefix in ["sub", "ses"], "`prefix` must be 'sub' or 'ses'."

    if not isinstance(names, List) or any(
        [not isinstance(ele, str) for ele in names]
    ):
        utils.log_and_raise_error(
            f"Ensure {prefix} names are a list of strings."
        )

    if any([" " in ele for ele in names]):
        utils.log_and_raise_error(f"{prefix} names cannot include spaces.")

    prefixed_names = ensure_prefixes_on_list_of_names(names, prefix)

    prefixed_names = update_names_with_range_to_flag(prefixed_names, prefix)

    update_names_with_datetime(prefixed_names)

    return prefixed_names


def check_names_for_duplicate_ids_and_inconsistent_leading_zeros(
    names: List[str], prefix: Literal["sub", "ses"]
) -> None:
    """
    Check a list of subject or session names for duplicate
    ids (e.g. [sub-001_@DATE@
    """
    prefix_values = utils.get_values_from_bids_formatted_name(
        names, prefix, return_as_int=False
    )

    leading_zeros = [num_leading_zeros(value) for value in prefix_values]
    int_values = [int(value) for value in prefix_values]

    if not all_identical(leading_zeros):
        utils.log_and_raise_error(
            f"The number of leading zeros within {prefix} names must be "
            f"consistent across all {prefix} names."
        )

    if not all_identical(int_values):
        utils.log_and_raise_error(
            f"{prefix} names must all have unique integer ids"
            f" after the {prefix} prefix."
        )


def all_unique(list_):
    return len(list_) == len(set(list_))


def all_identical(list_):
    return len(set(list_)) == 1


# Handle @TO@ flags  -------------------------------------------------------


def update_names_with_range_to_flag(
    names: List[str], prefix: str
) -> List[str]:
    """
    Given a list of names, check if they contain the @TO@ keyword.
    If so, expand to a range of names. Names including the @TO@
    keyword must be in the form prefix-num1@num2. The maximum
    number of leading zeros are used to pad the output
    e.g.
    sub-01@003 becomes ["sub-001", "sub-002", "sub-003"]

    Input can also be a mixed list e.g.
    names = ["sub-01", "sub-02@TO@04", "sub-05@TO@10"]
    will output a list of ["sub-01", ..., "sub-10"]
    """
    new_names = []

    for i, name in enumerate(names):
        if tags("to") in name:
            check_name_is_formatted_correctly(name, prefix)

            prefix_tag = re.search(f"{prefix}-[0-9]+{tags('to')}[0-9]+", name)[0]  # type: ignore
            tag_number = prefix_tag.split(f"{prefix}-")[1]

            name_start_str, name_end_str = name.split(tag_number)

            if tags("to") not in tag_number:
                utils.log_and_raise_error(
                    f"{tags('to')} flag must be between two numbers in the {prefix} tag."
                )

            left_number, right_number = tag_number.split(tags("to"))

            if int(left_number) >= int(right_number):
                utils.log_and_raise_error(
                    f"Number of the {prefix} to the  left of {tags('to')} flag "
                    f"must be smaller than the number to the right."
                )

            names_with_new_number_inserted = (
                make_list_of_zero_padded_names_across_range(
                    left_number, right_number, name_start_str, name_end_str
                )
            )
            new_names += names_with_new_number_inserted

        else:
            new_names.append(name)

    return new_names


def check_name_is_formatted_correctly(name: str, prefix: str) -> None:
    """
    Check the input string is formatted with the @TO@ key
    as expected.
    """
    first_key_value_pair = name.split("_")[0]
    expected_format = re.compile(f"{prefix}-[0-9]+{tags('to')}[0-9]+")

    if not re.fullmatch(expected_format, first_key_value_pair):
        utils.log_and_raise_error(
            f"The name: {name} is not in required format for {tags('to')} keyword. "
            f"The start must be  be {prefix}-<NUMBER>{tags('to')}<NUMBER>)."
        )


def make_list_of_zero_padded_names_across_range(
    left_number: str, right_number: str, name_start_str: str, name_end_str: str
) -> List[str]:
    """
    Numbers formatted with the @TO@ keyword need to have
    standardised leading zeros on the output. Here we take
    the maximum number of leading zeros and apply for
    all numbers in the range. Note int() will strip
    all leading zeros.

    Parameters
    ----------

    left_number : left (start) number from the range, e.g. "001"

    right_number : right (end) number from the range, e.g. "005"

    name_start_str : part of the name before the flag, usually "sub-"

    name_end_str : rest of the name after the flag, i.e. all other
        key-value pairs.
    """
    max_leading_zeros = max(
        num_leading_zeros(left_number), num_leading_zeros(right_number)
    )

    all_numbers = [*range(int(left_number), int(right_number) + 1)]

    all_numbers_with_leading_zero = [
        str(number).zfill(max_leading_zeros + 1) for number in all_numbers
    ]

    names_with_new_number_inserted = [
        f"{name_start_str}{number}{name_end_str}"
        for number in all_numbers_with_leading_zero
    ]

    return names_with_new_number_inserted


def num_leading_zeros(string: str) -> int:
    """int() strips leading zeros"""
    if string[:4] in ["sub-", "ses-"]:
        string = string[4:]

    return len(string) - len(str(int(string)))


# Handle @DATE@, @DATETIME@, @TIME@ flags -------------------------------------------------


def update_names_with_datetime(names: List[str]) -> None:
    """
    Replace @DATE@ and @DATETIME@ flag with date and datetime respectively.

    Format using key-value pair for bids, i.e. date-20221223_time-
    """
    date = str(datetime.datetime.now().date().strftime("%Y%m%d"))
    date_with_key = f"date-{date}"

    time_ = datetime.datetime.now().time().strftime("%H%M%S")
    time_with_key = f"time-{time_}"

    datetime_with_key = f"datetime-{date}T{time_}"

    for i, name in enumerate(names):
        # datetime conditional must come first.
        if tags("datetime") in name:
            name = add_underscore_before_after_if_not_there(
                name, tags("datetime")
            )
            names[i] = name.replace(tags("datetime"), datetime_with_key)

        elif tags("date") in name:
            name = add_underscore_before_after_if_not_there(name, tags("date"))
            names[i] = name.replace(tags("date"), date_with_key)

        elif tags("time") in name:
            name = add_underscore_before_after_if_not_there(name, tags("time"))
            names[i] = name.replace(tags("time"), time_with_key)


def add_underscore_before_after_if_not_there(string: str, key: str) -> str:
    """
    If names are passed with @DATE@, @TIME@, or @DATETIME@
    but not surrounded by underscores, check and insert
    if required. e.g. sub-001@DATE@ becomes sub-001_@DATE@
    or sub-001@DATEid-101 becomes sub-001_@DATE_id-101
    """
    key_len = len(key)
    key_start_idx = string.index(key)

    # Handle left edge
    if string[key_start_idx - 1] != "_":
        string_split = string.split(key)  # assumes key only in string once
        assert (
            len(string_split) == 2
        ), f"{key} must not appear in string more than once."

        string = f"{string_split[0]}_{key}{string_split[1]}"

    updated_key_start_idx = string.index(key)
    key_end_idx = updated_key_start_idx + key_len

    if key_end_idx != len(string) and string[key_end_idx] != "_":
        string = f"{string[:key_end_idx]}_{string[key_end_idx:]}"

    return string


def ensure_prefixes_on_list_of_names(
    all_names: Union[List[str], str], prefix: str
) -> List[str]:
    """
    Make sure all elements in the list of names are
    prefixed with the prefix, typically "sub-" or "ses-"

    Use expanded list for readability
    """
    prefix = prefix + "-"
    n_chars = len(prefix)

    new_names = []
    for name in all_names:
        if name[:n_chars] != prefix:
            new_names.append(prefix + name)
        else:
            new_names.append(name)

    return new_names


def check_datatype_is_valid(
    cfg: Configs, datatype: Union[List[str], str], error_on_fail: bool
) -> bool:
    """
    Check the passed datatype is valid (must
    be a key on self.ses_folders e.g. "behav", or "all")
    """
    if isinstance(datatype, list):
        valid_keys = list(cfg.datatype_folders.keys()) + ["all"]
        is_valid = all([type in valid_keys for type in datatype])
    else:
        is_valid = datatype in cfg.datatype_folders.keys() or datatype == "all"

    if error_on_fail and not is_valid:
        utils.log_and_raise_error(
            f"datatype: '{datatype}' "
            f"is not valid. Must be one of"
            f" {list(cfg.datatype_folders.keys())}. or 'all'"
            f" No folders were made."
        )

    return is_valid


def check_dashes_and_underscore_alternate_correctly(all_names):
    """ """
    for name in all_names:
        discrim = {"-": 1, "_": -1}
        dashes_underscores = [
            discrim[ele] for ele in name if ele in ["-", "_"]
        ]

        if dashes_underscores[0] != 1:
            utils.log_and_raise_error(
                "The first delimiter of 'sub' or 'ses' "
                "must be dash not underscore e.g. sub-001."
            )

        if len(dashes_underscores) % 2 != 0:
            dashes_underscores.pop(-1)

        if any([ele == 0 for ele in utils.diff(dashes_underscores)]):
            utils.log_and_raise_error(
                "Subject and session names must contain alternating dashes and "
                "underscores (used for separating key-value pairs)."
            )


# Sub or ses value length checks
# --------------------------------------------------------------------------------------


def warn_on_inconsistent_sub_or_ses_value_lengths(
    cfg: Configs,
):
    """
    Determine if there are inconsistent value lengths across the
    project (i.e. this local machine and the central machine.
    For example, there are inconsistent leading zeros in the list
    ["sub-001", "sub-02"], but not ["sub-001", "sub-002"]).

    If the number of sub or ses value lengths are not consistent (across local
    and remote repositories), then throw a warning. It is allowed for subjects
    and session folder names to have inconsistent leading zeros. But, within
    subject or session names, the value lengths must be consistent
    across local and central projects.
    """
    try:
        is_inconsistent = project_has_inconsistent_sub_or_ses_value_lengths(
            cfg
        )
    except:
        warnings.warn(
            "Could not search local and remote repositories. "
            "sub or ses key value length checks not performed."
        )
        return

    failing_cases = list(
        compress(
            ["sub", "ses"], [is_inconsistent["sub"], is_inconsistent["ses"]]
        )
    )

    if any(failing_cases):
        for fail_name in failing_cases:
            message = (
                f"Inconsistent value lengths for "
                f"the {fail_name} key in the project found. It is crucial "
                f"these are made consistent as soon as possible to "
                f"avoid unexpected behaviour of DataShuttle during "
                f"data transfer."
            )
            warnings.warn(message)

    else:
        utils.print_message_to_user(
            "No cases of inconsistent value lengths for subject or session"
            "found across this local machine and the central machine."
        )


def project_has_inconsistent_sub_or_ses_value_lengths(
    cfg: Configs,
) -> Dict:
    """
    Return bool indicating where the project (i.e. across
    both `local` and `central`) has consistent value lengths
    for sub and ses keys.
    It is not required that subjects and sessions have
    an equivalent value length (e.g.
    `sub-001`, `ses-01` is okay. But `sub-001`, `sub-02` is not.
    """
    folder_names = folders.get_all_sub_and_ses_names(cfg)

    subs_are_inconsistent = inconsistent_sub_or_ses_value_lengths(
        folder_names["sub"], "sub"
    )
    ses_are_inconsistent = inconsistent_sub_or_ses_value_lengths(
        folder_names["ses"], "ses"
    )
    return {"sub": subs_are_inconsistent, "ses": ses_are_inconsistent}


def inconsistent_sub_or_ses_value_lengths(
    all_names: List[str], sub_or_ses: Literal["sub", "ses"]
) -> bool:
    """
    Given a list of NeuroBlueprint-formatted subject or session names, determine if
    there are inconsistent value lengths for the sub or ses key.
    """
    all_numbers = utils.get_values_from_bids_formatted_name(
        all_names,
        sub_or_ses,
    )

    all_num_lens = [len(num) for num in all_numbers]

    if all_num_lens != [] and not identical_elements(all_num_lens):
        return True

    return False


def identical_elements(list_: List[Any]) -> bool:
    return len(set(list_)) == 1
