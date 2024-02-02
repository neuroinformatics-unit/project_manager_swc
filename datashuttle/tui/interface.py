from __future__ import annotations

import copy
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

if TYPE_CHECKING:
    import paramiko

    from datashuttle.configs.config_class import Configs
    from datashuttle.tui.app import App

from datashuttle import DataShuttle
from datashuttle.utils import ssh

Output = Tuple[bool, Any]


class Interface:
    """
    An interface class between the TUI and datashuttle API. Takes input
    to all datashuttle functions as passed from the TUI, outputs
    success status (True or False) and optional data, in the case
    of False.

    `self.project` is initialised when project is loaded.
    """

    def __init__(self) -> None:

        self.project: App
        self.name_templates: Dict = {}
        self.tui_settings: Dict = {}

    def select_existing_project(self, project_name: str) -> Output:
        """
        Load an existing project into `self.project`.

        Parameters
        ----------

        project_name : str
            The name of the datashuttle project to load.
            Must already exist.
        """
        try:
            project = DataShuttle(project_name)
            self.project = project
            return True, None

        except BaseException as e:
            return False, str(e)

    def setup_new_project(self, project_name: str, cfg_kwargs: Dict) -> Output:
        """
        Set up a new project and load into `self.project`.

        Parameters
        ----------

        project_name : str
            Name of the project to set up.

        cfg_kwargs : Dict
            The configurations to set the new project to. Note that
            some settings (e.g. `transfer_verbosity`) are not relevant
            for TUI and so method defaults will be used.
        """
        try:
            project = DataShuttle(project_name)

            project.make_config_file(**cfg_kwargs)

            self.project = project

            return True, None

        except BaseException as e:
            return False, str(e)

    def set_configs_on_existing_project(self, cfg_kwargs: Dict) -> Output:
        """
        Update the settings on an existing project. Only the settings
        passed in `cfg_kwargs` are updated.

        Parameters
        ----------

        cfg_kwargs : Dict
            The configs and new values to update.
        """
        try:
            self.project.update_config_file(**cfg_kwargs)
            return True, None

        except BaseException as e:
            return False, str(e)

    def create_folders(
        self,
        sub_names: List[str],
        ses_names: Optional[List[str]],
        datatype: List[str],
    ) -> Output:
        """
        Create folders through datashuttle.

        Parameters
        ----------

        sub_names : List[str]
            A list of un-formatted / validated

        """
        tmp_top_level_folder = self.project.get_top_level_folder()
        top_level_folder = self.tui_settings["top_level_folder_select"][
            "create_tab"
        ]

        try:
            self.project.set_top_level_folder(top_level_folder)
            self.project.create_folders(
                sub_names=sub_names, ses_names=ses_names, datatype=datatype
            )
            self.project.set_top_level_folder(tmp_top_level_folder)
            return True, None

        except BaseException as e:
            self.project.set_top_level_folder(tmp_top_level_folder)
            return False, str(e)

    def validate_names(
        self, sub_names: List[str], ses_names: Optional[List[str]]
    ) -> Output:
        """"""
        try:
            format_sub, format_ses = self.project._format_and_validate_names(
                sub_names,
                ses_names,
                self.get_name_templates(),
                bypass_validation=False,
            )

            return True, {
                "format_sub": format_sub,
                "format_ses": format_ses,
            }

        except BaseException as e:
            return False, str(e)

    # Transfer
    # ----------------------------------------------------------------------------------

    def transfer_entire_project(self, upload: bool) -> Output:
        try:
            if upload:
                self.project.upload_entire_project()
            else:
                self.project.download_entire_project()
            return True, None

        except BaseException as e:
            return False, str(e)

    def upload_top_level_only(
        self, selected_top_level_folder: str, upload: bool
    ) -> Output:
        """"""
        temp_top_level_folder = self.project.get_top_level_folder()
        self.project.set_top_level_folder(selected_top_level_folder)
        try:
            if upload:
                self.project.upload_all()
            else:
                self.project.download_all()

            self.project.set_top_level_folder(temp_top_level_folder)
            return True, None

        except BaseException as e:

            self.project.set_top_level_folder(temp_top_level_folder)
            return False, str(e)

    def transfer_custom_selection(
        self,
        selected_top_level_folder: str,
        sub_names: List[str],
        ses_names: List[str],
        datatype: List[str],
        upload: bool,
    ) -> Output:
        """"""
        temp_top_level_folder = self.project.get_top_level_folder()
        self.project.set_top_level_folder(selected_top_level_folder)

        try:
            if upload:
                self.project.upload(
                    sub_names=sub_names,
                    ses_names=ses_names,
                    datatype=datatype,
                )
            else:
                self.project.download(
                    sub_names=sub_names,
                    ses_names=ses_names,
                    datatype=datatype,
                )

            self.project.set_top_level_folder(temp_top_level_folder)
            return True, None

        except BaseException as e:

            self.project.set_top_level_folder(temp_top_level_folder)
            return False, str(e)

    # Setup SSH
    # ----------------------------------------------------------------------------------

    def get_name_templates(self) -> Dict:
        # Hold in a var to stop file read every time this is called.
        if not self.name_templates:
            self.name_templates = self.project.get_name_templates()

        return self.name_templates  # TODO: handle properly

    def set_name_templates(self, templates: Dict) -> Output:
        try:
            self.project.set_name_templates(templates)
            self.name_templates = templates
            return True, None

        except BaseException as e:
            return False, str(e)

    def get_tui_settings(self) -> Dict:
        if not self.tui_settings:
            self.tui_settings = self.project._load_persistent_settings()["tui"]

        return self.tui_settings

    def update_tui_settings(
        self, value: Any, key: str, key_2: Optional[str] = None
    ) -> None:

        if key_2 is None:
            self.tui_settings[key] = value
        else:
            self.tui_settings[key][key_2] = value

        self.project._update_persistent_setting("tui", self.tui_settings)

    # Setup SSH
    # ----------------------------------------------------------------------------------

    def get_central_host_id(self) -> str:
        return self.project.cfg["central_host_id"]

    def get_configs(self) -> Configs:
        return self.project.cfg

    def get_textual_compatible_project_configs(self) -> Configs:
        cfg_to_load = copy.deepcopy(self.project.cfg)
        cfg_to_load.convert_str_and_pathlib_paths(
            cfg_to_load, "path_to_str"
        )  # TODO: bit weird...
        return cfg_to_load

    def get_next_sub_number(self) -> str:
        return self.project.get_next_sub_number(
            return_with_prefix=True, local_only=True
        )

    def get_next_ses_number(self, sub: str) -> str:
        return self.project.get_next_ses_number(
            sub, return_with_prefix=True, local_only=True
        )

    def get_ssh_hostkey(self) -> Output:

        try:
            key = ssh.get_remote_server_key(
                self.project.cfg["central_host_id"]
            )
            return True, key
        except BaseException as e:
            return False, str(e)

    def save_hostkey_locally(self, key: paramiko.RSAKey) -> Output:

        try:
            ssh.save_hostkey_locally(
                key,
                self.project.cfg["central_host_id"],
                self.project.cfg.hostkeys_path,
            )
            return True, None

        except BaseException as e:
            return False, str(e)

    def setup_key_pair_and_rclone_config(self, password: str) -> Output:

        try:
            ssh.add_public_key_to_central_authorized_keys(
                self.project.cfg, password, log=False
            )
            self.project._setup_rclone_central_ssh_config(log=False)

            return True, None

        except BaseException as e:
            return False, str(e)
