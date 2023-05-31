# flake8: noqa
# fmt: off

from pathlib import Path

import pandas as pd


def get_pathtable(base_folder):

    columns = ["base_folder", "path", "is_non_sub", "is_non_ses", "is_ses_level_non_data_type", "parent_sub", "parent_ses", "parent_data_type"]

#   base_folder                                  path                                                                          is_non_sub   is_non_ses  is_ses_level_non_data_type   parent_sub                  parent_ses                  parent_data_type
    data = [[base_folder, Path("rawdata") / "sub-001" / "ses-001" / "sub-001_ses-001_data-file",                                False,      False,       True,                       "sub-001",                  "ses-001",                  None],
            [base_folder, Path("rawdata") / "sub-001" / "ses-002_random-key" / "random-key-file.mp4",                           False,      False,       True,                       "sub-001",                  "ses-002_random-key",       None],
            [base_folder, Path("rawdata") / "sub-001" / "ses-003_date-20231901" / "behav" / "behav.csv",                        False,      False,       False,                      "sub-001",                  "ses-003_date-20231901",    "behav"],
            [base_folder, Path("rawdata") / "sub-001" / "ses-003_date-20231901" / "ephys" / "ephys.bin",                        False,      False,       False,                      "sub-001",                  "ses-003_date-20231901",    "ephys"],
            [base_folder, Path("rawdata") / "sub-001" / "ses-003_date-20231901" / "non_data" / "non_data.mp4",                  False,      False,       True,                       "sub-001",                  "ses-003_date-20231901",    None],
            [base_folder, Path("rawdata") / "sub-001" / "ses-003_date-20231901" / "nondata_type_level_file.csv",                False,      False,       True,                       "sub-001",                  "ses-003_date-20231901",    None],
            [base_folder, Path("rawdata") / "sub-001" / "random-ses_level_file.mp4",                                            False,      True,        False,                      "sub-001",                  None,                       None],
            [base_folder, Path("rawdata") / "sub-001" / "histology" / "sub-001_histology.file",                                 False,      False,       False,                      "sub-001",                  None,                       "histology"],
            [base_folder, Path("rawdata") / "sub-002_random-value" / "sub-002_random-value.file",                               False,      True,        False,                      "sub-002_random-value",     None,                       None],
            [base_folder, Path("rawdata") / "sub-002_random-value" / "ses-001" / "non_data_type_level_folder" / "file.csv",        False,      False,       True,                       "sub-002_random-value",     "ses-001",                  None],
            [base_folder, Path("rawdata") / "sub-003_date-20231901" / "ses-001" / "funcimg" / ".myfile.xlsx",                   False,      False,       False,                      "sub-003_date-20231901",    "ses-001",                  "funcimg"],
            [base_folder, Path("rawdata") / "sub-003_date-20231901" / "ses-003_date-20231901" / "nondata_type_level_file.csv",  False,      False,       True,                       "sub-003_date-20231901",    "ses-003_date-20231901",    None],
            [base_folder, Path("rawdata") / "sub-003_date-20231901" / "ses-003_date-20231901" / "funcimg" / "funcimg.nii",      False,      False,       False,                      "sub-003_date-20231901",    "ses-003_date-20231901",    "funcimg"],
            [base_folder, Path("rawdata") / "sub-003_date-20231901" / "seslevel_non-prefix_folder" / "nonlevel.mat",               False,      True,        False,                      "sub-003_date-20231901",    "seslevel_non-prefix_folder",  None],
            [base_folder, Path("rawdata") / "sub-003_date-20231901" / "sub-ses-level_file.txt",                                 False,      True,        False,                      "sub-003_date-20231901",    None,                       None],
            [base_folder, Path("rawdata") / "sub-003_date-20231901" / "histology" / ".histology.file",                          False,      False,       False,                      "sub-003_date-20231901",    None,                       "histology"],
            [base_folder, Path("rawdata") / "project_level_file.txt",                                                           True,       False,       False,                      None,                       None,                       None],
            [base_folder, Path("rawdata") / "sublevel_non_sub-prefix_folder" / "ses_non_folder.file",                                 True,       False,       False,                      None,                       None,                       None],
            ]


    pathtable = pd.DataFrame(data, columns=columns)

    return pathtable
# fmt: on
