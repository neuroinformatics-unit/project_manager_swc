"""
"""

import copy
from pathlib import Path

import pandas as pd
import pytest
import test_utils
from base import BaseTest
from file_conflicts_pathtable import get_pathtable


class BaseTransfer(BaseTest):

    # ----------------------------------------------------------------------------------
    # Test File Transfer - All Options
    # ----------------------------------------------------------------------------------

    @pytest.fixture(
        scope="class",
    )
    def pathtable_and_project(self, tmpdir_factory):
        """
        Create a new test project with a test project folder
        and file structure (see `get_pathtable()` for definition).
        """
        tmp_path = tmpdir_factory.mktemp("test")

        base_path = tmp_path / "test with space"
        test_project_name = "test_file_conflicts"

        project, cwd = test_utils.setup_project_fixture(
            base_path, test_project_name
        )

        pathtable = get_pathtable(project.cfg["local_path"])

        self.create_all_pathtable_files(pathtable)

        yield [pathtable, project]

        test_utils.teardown_project(cwd, project)

    def get_expected_transferred_paths(
        self, pathtable, sub_names, ses_names, datatype
    ):
        """
        Process the expected files that are transferred using the logic in
        `make_pathtable_search_filter()` to
        """
        parsed_sub_names = self.parse_arguments(pathtable, sub_names, "sub")
        parsed_ses_names = self.parse_arguments(pathtable, ses_names, "ses")
        parsed_datatype = self.parse_arguments(pathtable, datatype, "datatype")

        # Filter pathtable to get files that were expected to be transferred
        (
            sub_ses_dtype_arguments,
            extra_arguments,
        ) = self.make_pathtable_search_filter(
            parsed_sub_names, parsed_ses_names, parsed_datatype
        )

        datatype_folders = self.query_table(pathtable, sub_ses_dtype_arguments)
        extra_folders = self.query_table(pathtable, extra_arguments)

        expected_paths = pd.concat([datatype_folders, extra_folders])
        expected_paths = expected_paths.drop_duplicates(subset="path")

        expected_paths = self.remove_path_before_rawdata(expected_paths.path)

        return expected_paths

    def make_pathtable_search_filter(self, sub_names, ses_names, datatype):
        """
        Create a string of arguments to pass to pd.query() that will
        create the table of only transferred sub, ses and datatype.

        Two arguments must be created, one of all sub / ses / datatypes
        and the other of all non sub/ non ses / non datatype
        folders. These must be handled separately as they are
        mutually exclusive.
        """
        sub_ses_dtype_arguments = []
        extra_arguments = []

        for sub in sub_names:
            if sub == "all_non_sub":
                extra_arguments += ["is_non_sub == True"]
            else:
                for ses in ses_names:
                    if ses == "all_non_ses":
                        extra_arguments += [
                            f"(parent_sub == '{sub}' & is_non_ses == True)"
                        ]
                    else:
                        for dtype in datatype:
                            if dtype == "all_non_datatype":
                                extra_arguments += [
                                    f"(parent_sub == '{sub}' & parent_ses == '{ses}' "
                                    f"& is_ses_level_non_datatype == True)"
                                ]
                            else:
                                sub_ses_dtype_arguments += [
                                    f"(parent_sub == '{sub}' & parent_ses == '{ses}' "
                                    f"& (parent_datatype == '{dtype}' "
                                    f"| parent_datatype == '{dtype}'))"
                                ]

        return sub_ses_dtype_arguments, extra_arguments

    def remove_path_before_rawdata(self, list_of_paths):
        """
        Remove the path to project files before the "rawdata" so
        they can be compared no matter where the project was stored
        (e.g. on a central server vs. local filesystem).
        """
        cut_paths = []
        for path_ in list_of_paths:
            parts = Path(path_).parts
            cut_paths.append(Path(*parts[parts.index("rawdata") :]))
        return cut_paths

    def query_table(self, pathtable, arguments):
        """
        Search the table for arguments, return empty
        if arguments empty
        """
        if any(arguments):
            folders = pathtable.query(" | ".join(arguments))
        else:
            folders = pd.DataFrame()
        return folders

    def parse_arguments(self, pathtable, list_of_names, field):
        """
        Replicate datashuttle name formatting by parsing
        "all" arguments and turning them into a list of all names,
        (subject or session), taken from the pathtable.
        """
        if list_of_names in [["all"], [f"all_{field}"]]:
            entries = pathtable.query(f"parent_{field} != False")[
                f"parent_{field}"
            ]
            entries = list(set(entries))
            if list_of_names == ["all"]:
                entries += (
                    [f"all_non_{field}"]
                    if field != "datatype"
                    else ["all_non_datatype"]
                )
            list_of_names = entries
        return list_of_names

    def create_all_pathtable_files(self, pathtable):
        """
        Create the entire test project in the defined
        location (usually project's `local_path`).
        """
        for i in range(pathtable.shape[0]):
            filepath = pathtable["base_folder"][i] / pathtable["path"][i]
            filepath.parents[0].mkdir(parents=True, exist_ok=True)
            test_utils.write_file(filepath, contents="test_entry")

    def central_from_local(self, path_):
        return Path(str(copy.copy(path_)).replace("local", "central"))
