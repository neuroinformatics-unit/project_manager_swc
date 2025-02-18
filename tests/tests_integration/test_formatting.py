import pytest
from base import BaseTest

from datashuttle.utils import formatting
from datashuttle.utils.custom_exceptions import NeuroBlueprintError


class TestFormatting(BaseTest):
    @pytest.mark.parametrize("prefix", ["sub", "ses"])
    @pytest.mark.parametrize(
        "input", [1, {"test": "one"}, 1.0, ["1", "2", ["three"]]]
    )
    def test_format_names_bad_input(self, input, prefix):
        """
        Test that names passed in incorrect type
        (not str, list) raise appropriate error.
        """
        with pytest.raises(TypeError) as e:
            formatting.format_names(input, prefix)

        assert f"Ensure {prefix} names are a list of strings." == str(e.value)

    @pytest.mark.parametrize("prefix", ["sub", "ses"])
    def test_format_names_duplicate_ele(self, prefix):
        """
        Test that appropriate error is raised when duplicate name
        is passed to format_names().
        """
        with pytest.raises(NeuroBlueprintError) as e:
            formatting.check_and_format_names(
                ["1", "2", "3", "3", "4"], prefix
            )

        assert (
            f"{prefix} names must all have unique integer "
            f"ids after the {prefix} prefix." == str(e.value)
        )

    def test_format_names_prefix(self):
        """
        Check that format_names correctly prefixes input
        with default sub or ses prefix. This is less useful
        now that ses/sub name dash and underscore order is
        more strictly checked.
        """
        prefix = "sub"

        # check name is prefixed
        formatted_names = formatting.format_names(["1"], prefix)
        assert formatted_names[0] == "sub-1"

        # check existing prefix is not duplicated
        formatted_names = formatting.format_names(["sub-1"], prefix)
        assert formatted_names[0] == "sub-1"

        # test mixed list of prefix and unprefixed are prefixed correctly.
        mixed_names = ["1", prefix + "-four", "5", prefix + "-6"]
        formatted_names = formatting.format_names(mixed_names, prefix)
        assert formatted_names == [
            "sub-1",
            "sub-four",
            "sub-5",
            "sub-6",
        ]

    @pytest.mark.parametrize("top_level_folder", ["rawdata", "derivatives"])
    @pytest.mark.parametrize("project", ["local", "full"], indirect=True)
    def test_warning_non_consecutive_numbers(self, project, top_level_folder):
        project.create_folders(
            top_level_folder,
            ["sub-01", "sub-02", "sub-04"],
            ["ses-05", "ses-10"],
        )

        with pytest.warns(UserWarning) as w:
            project.get_next_sub(top_level_folder)
        assert (
            str(w[0].message) == "A subject number has been skipped, "
            "currently used subject numbers are: [1, 2, 4]"
        )

        with pytest.warns(UserWarning) as w:
            project.get_next_ses(top_level_folder, "sub-02")
        assert (
            str(w[0].message)
            == "A subject number has been skipped, currently "
            "used subject numbers are: [5, 10]"
        )
