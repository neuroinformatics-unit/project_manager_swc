import subprocess
from pathlib import Path
from subprocess import CompletedProcess
from typing import Dict, List, Literal

from datashuttle.configs.config_class import Configs
from datashuttle.utils import utils


def call_rclone(command: str, pipe_std: bool = False) -> CompletedProcess:
    """
    Call rclone with the specified command. Current mode is double-verbose.
    Return the completed process from subprocess.

    Parameters
    ----------
    command: Rclone command to be run

    pipe_std: if True, do not output anything to stdout.
    """
    command = "rclone " + command
    if pipe_std:
        output = subprocess.run(
            command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True
        )
    else:
        output = subprocess.run(command, shell=True)

    return output


# -----------------------------------------------------------------------------
# Setup
# -----------------------------------------------------------------------------


def setup_central_as_rclone_target(
    connection_method: Literal["ssh", "local_filesystem"],
    cfg: Configs,
    rclone_config_name: str,
    ssh_key_path: Path,
    log: bool = True,
) -> None:
    """
     RClone sets remote targets in a config file. When
     copying to central, use the syntax remote: to
     identify the central to copy to. Note rclone calls
    the target machine 'remote' and we call it 'central'.

     For local filesystem, this is just a placeholder and
     the config contains no further information.

     For SSH, this contains information for
     connecting to central with SSH.

     Parameters
     ----------

    connection_method : Literal["ssh", "local_filesystem"]
        Method to connect with central machine.

     cfg : Configs
        datashuttle configs UserDict.

     rclone_config_name : rclone config name
         generated by datashuttle.cfg.get_rclone_config_name()

     ssh_key_path : path to the ssh key used for connecting to
         ssh central filesystem, if config "connection_method" is "ssh".

     log : whether to log, if True logger must already be initialised.
    """
    if connection_method == "local_filesystem":
        call_rclone(f"config create {rclone_config_name} local", pipe_std=True)

    elif connection_method == "ssh":
        call_rclone(
            f"config create "
            f"{rclone_config_name} "
            f"sftp "
            f"host {cfg['central_host_id']} "
            f"user {cfg['central_host_username']} "
            f"port 22 "
            f"key_file {ssh_key_path.as_posix()}",
            pipe_std=True,
        )

    output = call_rclone("config file", pipe_std=True)

    if log:
        utils.log(
            f"Successfully created rclone config. "
            f"{output.stdout.decode('utf-8')}"
        )


def check_rclone_with_default_call() -> bool:
    """
    Check to see whether rclone is installed.
    """
    try:
        output = call_rclone("-h", pipe_std=True)
    except FileNotFoundError:
        return False
    return True if output.returncode == 0 else False


def prompt_rclone_download_if_does_not_exist() -> None:
    """
    Check that rclone is installed. If it does not
    (e.g. first time using datashuttle) then download.
    """
    if not check_rclone_with_default_call():
        raise BaseException(
            "RClone installation not found. Install by entering "
            "the following into your terminal:\n"
            " conda install -c conda-forge rclone"
        )


# -----------------------------------------------------------------------------
# Transfer
# -----------------------------------------------------------------------------


def transfer_data(
    cfg: Configs,
    upload_or_download: Literal["upload", "download"],
    include_list: List[str],
    rclone_options: Dict,
) -> subprocess.CompletedProcess:
    """
    Transfer data by making a call to Rclone.

    Parameters
    ----------

    cfg: Configs
        datashuttle configs

    upload_or_download : Literal["upload", "download"]
        If "upload", transfer from `local_path` to `central_path`.
        "download" proceeds in the opposite direction.

    include_list : List[str]
        A list of filepaths to include in the transfer

    rclone_options : Dict
        A list of options to pass to Rclone's copy function.
        see `cfg.make_rclone_transfer_options()`.
    """
    assert upload_or_download in [
        "upload",
        "download",
    ], "must be 'upload' or 'download'"

    local_filepath = cfg.get_base_folder("local").as_posix()
    central_filepath = cfg.get_base_folder("central").as_posix()

    extra_arguments = handle_rclone_arguments(rclone_options, include_list)

    if upload_or_download == "upload":
        output = call_rclone(
            f"{rclone_args('copy')} "
            f'"{local_filepath}" "{cfg.get_rclone_config_name()}:'
            f'{central_filepath}" {extra_arguments}',
            pipe_std=True,
        )

    elif upload_or_download == "download":
        output = call_rclone(
            f"{rclone_args('copy')} "
            f'"{cfg.get_rclone_config_name()}:'
            f'{central_filepath}" "{local_filepath}"  {extra_arguments}',
            pipe_std=True,
        )

    return output


def handle_rclone_arguments(
    rclone_options: Dict, include_list: List[str]
) -> str:
    """
    Construct the extra arguments to pass to RClone based on the
    current configs.
    """
    extra_arguments_list = []

    extra_arguments_list += ["-" + rclone_options["transfer_verbosity"]]

    if not rclone_options["overwrite_old_files"]:
        extra_arguments_list += [rclone_args("ignore_existing")]

    if rclone_options["show_transfer_progress"]:
        extra_arguments_list += [rclone_args("progress")]

    if rclone_options["dry_run"]:
        extra_arguments_list += [rclone_args("dry_run")]

    extra_arguments_list += include_list

    extra_arguments = " ".join(extra_arguments_list)

    return extra_arguments


def rclone_args(name: str) -> str:
    """
    Central function to hold rclone commands
    """
    valid_names = ["dry_run", "copy", "ignore_existing", "progress"]
    assert name in valid_names, f"`name` must be in: {valid_names}"

    if name == "dry_run":
        arg = "--dry-run"

    if name == "copy":
        arg = "copy"

    if name == "ignore_existing":
        arg = "--ignore-existing"

    if name == "progress":
        arg = "--progress"

    return arg
