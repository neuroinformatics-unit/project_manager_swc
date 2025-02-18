def get_tooltip(id: str) -> str:
    """
    Master function to get tooltips for all widgets,
    based on their widget (textual) id.
    """
    # Configs
    # -------------------------------------------------------------------------

    # project_name input
    if id == "#configs_name_input":
        tooltip = "The name of the project. Cannot contain special characters (e.g. !@?) or spaces."

    # local path input
    elif id == "#configs_local_path_input":
        tooltip = (
            "Path to the project folder on the local machine, where acquired data will be saved.\n\n"
            "The project folder name must be the same as the project name. Input a path directly to "
            "the project folder, or it's parent folder (and it will be created automatically)."
        )

    # connection method label
    elif id == "#configs_connect_method_label":
        tooltip = "Method to connect to the central data storage machine."

    # local filesystem radiobutton
    elif id == "#configs_local_filesystem_radiobutton":
        tooltip = (
            "Use local filesystem when the central data storage "
            "is a mounted drive on your current machine."
        )

    # SSH radiobutton
    elif id == "#configs_ssh_radiobutton":
        tooltip = "Use SSH when planning to connect with the central data storage via SSH protocol."

    # No connection (local only) radiobutton
    elif id == "#configs_local_only_radiobutton":
        tooltip = "No connection to a central project is made.\nTransfer functionality will not be available."

    # central host input
    elif id == "#configs_central_host_id_input":
        tooltip = "The hostname or IP address of the server."

    # central host username input
    elif id == "#configs_central_host_username_input":
        tooltip = "The account username through which to access the server."

    # central path input
    elif id == "config_central_path_input_mode-ssh":
        tooltip = (
            "The path to the project folder on the central machine (or it's parent folder).\n\n"
            "With 'SSH', this path is relative to the server e.g. /nhome/users/myusername"
        )

    elif id == "config_central_path_input_mode-local_filesystem":
        tooltip = (
            "The path to the project folder on the central machine (or it's parent folder).\n\n"
            "With 'local filesystem', this path is relative to the current machine and directs "
            "to a project folder, possibly on a mounted drive.\n\n"
        )

    # Settings
    # -------------------------------------------------------------------------

    # Show transfer status on directory tree checkbox
    elif id == "#show_transfer_tree_status_checkbox":
        tooltip = (
            "Display the status of files on the project manager page's "
            "`Transfer` directory tree (e.g. file colour indicates changes "
            "between central and local projects).\n\n"
            "Note that this may cause performance issues, in particular when "
            "using an SSH connection."
        )

    # Tabscreen - Create tab
    # -------------------------------------------------------------------------

    # directorytree
    elif id == "#create_folders_directorytree":
        tooltip = (
            "The local project folder. Provides a number of convenient shortcuts "
            "when hovering the mouse over a folder:\n\n"
            "-CTRL+O : open the folder in the system filebrowser.\n"
            "-CTRL+N : rename a file or folder.\n"
            "-CTRL+Q : copy the full filepath to clipboard.\n"
            "-CTRL+R : refresh the folder tree.\n"
            "-CTRL+F : fill the 'sub-' or 'ses-' input with the foldername.\n"
            "-CTRL+A : similar to CTRL+F, but append."
        )

    # subect / session label (explain input)
    elif id == "#create_folders_subject_input":
        tooltip = "Input subject here. Will show live validation."

    # subect / session label (explain input)
    elif id == "#create_folders_session_input":
        tooltip = "Input session here. Will show live validation."

    # initial tooltip on the subject / session inputs
    elif id == "#create_folders_subject_label":
        tooltip = (
            "The subject to create. Double-click the input to suggest the next subject.\n\n"
            "Hold CTRL when clicking to suggest onlu the prefix (with template, if on in 'Settings')."
        )

    # initial tooltip on the subject / session inputs
    elif id == "#create_folders_session_label":
        tooltip = (
            "The session to create. Auto-fill with the same shortcuts as subject input.\n\n"
            "The suggested session will be for the subject input above."
        )

    # datatype label
    elif id == "#create_folders_datatype_label":
        tooltip = "The datatypes to create in the session folder."

    # Tabscreen - Settings page
    # -------------------------------------------------------------------------

    # top level folder select
    elif id == "#create_folders_settings_toplevel_select":
        tooltip = "The top-level-folder to create folders in."

    # bypass validation checkbox
    elif id == "#create_folders_settings_bypass_validation_checkbox":
        tooltip = (
            "Allow folder creation even when there is a validation error."
        )

    # template validation checkbox
    elif id == "#template_settings_validation_on_checkbox":
        tooltip = "Turn on the 'name templates' feature."

    # Tabscreen - Tranfser tab
    # -------------------------------------------------------------------------

    # directorytree
    elif id == "#transfer_directorytree":
        tooltip = (
            "Shows the local project tree. Transfer status highlighting "
            "can be turned on at the Main Menu 'Settings' page.\n\n"
            "Keyboard shortcuts, when hovering the mouse over a folder:\n\n"
            "-CTRL+O : open the folder in the system filebrowser.\n"
            "-CTRL+N : rename a file or folder.\n"
            "-CTRL+Q : copy the full filepath to clipboard.\n"
            "-CTRL+R : refresh the folder tree.\n"
            "-CTRL+F : fill the 'sub-' or 'ses-' input with the foldername.\n"
            "-CTRL+A : similar to CTRL+F, but append."
        )

    # Upload / Download
    elif id == "#transfer_switch_container":
        tooltip = (
            "Upload (local to central) or \n Download (central to local)."
        )

    elif id == "#transfer_tab_overwrite_select":
        tooltip = (
            "Determine whether source file will overwrite destination.\n\n"
            "'never': destination file will never be overwritten.\n\n"
            "'always': destination file will always be overwritten if "
            "source and destination differ in size or datetime.\n\n"
            "'if source newer': destination will only be overwritten "
            "if the source file is newer."
        )

    # Dry Run
    elif id == "#transfer_tab_dry_run_checkbox":
        tooltip = (
            "Perform a dry-run to test what will happenen during transfer.\n\n"
            "Logs will be written, but no data will actually be transferred."
        )

    # custom subject input
    elif id == "#transfer_subject_input":
        tooltip = (
            "Name of names of subjects to transfer. If multiple subjects"
            "are input, separate with a comma e.g. sub-001, sub-002.\n\n"
            "The range tag @TO@ can be use to transfer a range of subjects e.g. sub-001@TO@sub-005\n\n"
            "Wildcard tag @*@ can be use to match any part of a filename e.g. sub-001_date-@*@.\n\n"
            "Use 'all' to transfer all subject and non-subect folders in the top-level-folder.\n\n"
            "Use 'all_sub' to transfer all subject folders only (i.e. starting with 'sub-' prefix).\n\n"
            "Use 'all_non_sub' to transfer all other folders only (i.e. that do not start with the 'sub-' prefix)."
        )

    # custom session input
    elif id == "#transfer_session_input":
        tooltip = (
            "Name of names of sessions to transfer. If multiple sessions"
            "are input, separate with a comma e.g. ses-001, ses-002.\n\n"
            "The range tag @TO@ can be use to transfer a range of subjects e.g. ses-001@TO@ses-005\n\n"
            "Wildcard tag @*@ can be use to match any part of a filename e.g. ses-001_date-@*@.\n\n"
            "Use 'all' to transfer all session and non-session folders within subjects.\n\n"
            "Use 'all_ses' to transfer all session folders only (i.e. starting with 'ses-' prefix).\n\n"
            "Use 'all_non_ses' to transfer all other folders only (i.e. that do not start with the 'ses-' prefix)."
        )

    # 'all', 'all datatype', 'all non datatype'
    elif id == "#transfer_all_checkbox":
        tooltip = "Select to transfer all datatype and non-datatype folders within sessions."

    elif id == "#transfer_all_datatype_checkbox":
        tooltip = "Select to transfer all datatype folders, but not non-datatype folders, from within sessions."

    elif id == "#transfer_all_non_datatype_checkbox":
        tooltip = "Select to transfer only non-datatype folders from within sessions."

    return tooltip
