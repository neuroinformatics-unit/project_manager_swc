from typing import Dict, List, Optional, Tuple

import paramiko

from datashuttle import DataShuttle
from datashuttle.utils import formatting, ssh, validation

Output = Tuple[bool, Optional[str]]  # TODO: rename


class DsInterface:
    """
    An interface class between the TUI and datashuttle API. Takes input
    to all datashuttle functions as passed from the TUI, outputs
    success status (True or False) and optional data, in the case
    of False.
    """

    def __init__(self):

        self.project: App

    def select_existing_project(self, project_name: str) -> Output:

        try:
            project = DataShuttle(project_name)
            self.project = project
            return True, None

        except BaseException as e:
            return False, str(e)

    def setup_new_project(self, project_name: str, cfg_kwargs: Dict) -> Output:

        try:
            project = DataShuttle(project_name)

            project.make_config_file(**cfg_kwargs)

            self.project = project

            return True, None

        except BaseException as e:
            return False, str(e)

    def set_configs_on_existing_project(self, cfg_kwargs: Dict) -> Output:

        try:
            self.project.update_config_file(**cfg_kwargs)
            return True, None

        except BaseException as e:
            return False, str(e)

    def create_folders(
        self, sub_names: List[str], ses_names: List[str], datatype: List[str]
    ) -> Output:

        # This can't use the top level folder argument on the select
        # because it is on another screen, which is not good...
        # In general this handling of top level folder is not ideal...
        tmp_top_level_folder = (
            self.project.get_top_level_folder()
        )  # TODO: make very clear how this is set, bit of a mess ATM, all over the place. centralise!
        persistent_settings = self.project._load_persistent_settings()
        top_level_folder = persistent_settings["tui"][
            "top_level_folder_select"
        ]["create_tab"]

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
        self, sub_names: List[str], ses_names: List[str], templates: Dict
    ) -> Output:
        """"""
        try:
            format_sub = formatting.check_and_format_names(
                sub_names, "sub", name_templates=templates
            )

            if ses_names is not None:
                format_ses = formatting.check_and_format_names(
                    ses_names, "ses", name_templates=templates
                )
            else:
                format_ses = None

            validation.validate_names_against_project(
                self.project.cfg,
                format_sub,
                format_ses,
                local_only=True,
                error_or_warn="error",
                log=False,
                name_templates=templates,
            )

            return True, {
                "format_sub": format_sub,
                "format_ses": format_ses,
            }

        except BaseException as e:
            return False, str(e)

    # Transfer
    # ----------------------------------------------------------------------------------

    def transfer_entire_project(self, upload: bool):
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

    def get_central_host_id(self) -> str:
        return self.project.cfg["central_host_id"]

    def get_ssh_hostkey(self):

        try:
            key = ssh.get_remote_server_key(
                self.project.cfg["central_host_id"]
            )
            return True, key
        except BaseException as e:
            return False, str(e)

    def save_hostkey_locally(self, key: paramiko.RSAKey):

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
