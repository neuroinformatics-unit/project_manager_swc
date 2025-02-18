from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datashuttle.configs.config_class import Configs

import fnmatch
import getpass
import stat
import sys
from pathlib import Path
from typing import Any, List, Optional, Tuple

import paramiko

from datashuttle.utils import utils

# -----------------------------------------------------------------------------
# Core Functions
# -----------------------------------------------------------------------------
# These functions are called by both API and TUI.
# Unfortunately it is not possible for TUI to call API directly in the case of
# setting up SSH, because it requires user input to proceed.


def connect_client_core(
    client: paramiko.SSHClient,
    cfg: Configs,
    password: Optional[str] = None,
):
    client.get_host_keys().load(cfg.hostkeys_path.as_posix())
    client.set_missing_host_key_policy(paramiko.RejectPolicy())

    client.connect(
        cfg["central_host_id"],
        username=cfg["central_host_username"],
        password=password,
        key_filename=(
            cfg.ssh_key_path.as_posix()
            if isinstance(cfg.ssh_key_path, Path)
            else None
        ),
        look_for_keys=True,
    )


def add_public_key_to_central_authorized_keys(
    cfg: Configs, password: str, log=True
) -> None:
    """
    Append the public part of key to central server ~/.ssh/authorized_keys.
    """
    generate_and_write_ssh_key(cfg.ssh_key_path)

    key = paramiko.RSAKey.from_private_key_file(cfg.ssh_key_path.as_posix())

    client: paramiko.SSHClient
    with paramiko.SSHClient() as client:
        if log:
            connect_client_with_logging(client, cfg, password=password)
        else:
            connect_client_core(client, cfg, password=password)

        client.exec_command("mkdir -p ~/.ssh/")
        client.exec_command(
            # double >> for concatenate
            f'echo "{key.get_name()} {key.get_base64()}" '
            f">> ~/.ssh/authorized_keys"
        )
        client.exec_command("chmod 644 ~/.ssh/authorized_keys")
        client.exec_command("chmod 700 ~/.ssh/")


def generate_and_write_ssh_key(ssh_key_path: Path) -> None:
    key = paramiko.RSAKey.generate(4096)
    key.write_private_key_file(ssh_key_path.as_posix())


def get_remote_server_key(central_host_id: str):
    """
    Get the remove server host key for validation before
    connection.
    """
    transport: paramiko.Transport
    with paramiko.Transport(central_host_id) as transport:
        transport.connect()
        key = transport.get_remote_server_key()
    return key


def save_hostkey_locally(key, central_host_id, hostkeys_path) -> None:
    client = paramiko.SSHClient()
    client.get_host_keys().add(central_host_id, key.get_name(), key)
    client.get_host_keys().save(hostkeys_path.as_posix())


# -----------------------------------------------------------------------------
# Setup SSH - API Wrappers
# -----------------------------------------------------------------------------
# These functions wrap core SSH setup functions (above) for the API. See
# tui/screens/setup_ssh for the TUI equivalents.


def setup_ssh_key(
    cfg: Configs,
    log: bool = True,
) -> None:
    """
    Set up an SSH private / public key pair with
    central server. First, a private key is generated
    and saved in the .datashuttle config path.
    Next a connection requiring input
    password made, and the public part of the key
    added to ~/.ssh/authorized_keys.

    Parameters
    -----------

    ssh_key_path : path to the ssh private key

    hostkeys_path : path to the ssh host key, once the user
        has confirmed the key ID this is saved so verification
        is not required each time.

    cfg : datashuttle config UserDict

    log : log if True, logger must already be initialised.
    """
    if not sys.stdin.isatty():
        proceed = input(
            "\nWARNING!\nThe next step is to enter a password, but it is not possible\n"
            "to hide your password while entering it in the current terminal.\n"
            "This can occur if running the command in an IDE.\n\n"
            "Press 'y' to proceed to password entry. "
            "The characters will not be hidden!\n"
            "Alternatively, run ssh setup after starting Python in your "
            "system terminal \nrather than through an IDE: "
        )
        if proceed != "y":
            utils.print_message_to_user(
                "Quitting SSH setup as 'y' not pressed."
            )
            return

        password = input(
            "Please enter your password. Characters will not be hidden: "
        )
    else:
        password = getpass.getpass(
            "Please enter password to your central host to add the public key. "
            "You will not have to enter your password again."
        )

    add_public_key_to_central_authorized_keys(cfg, password)

    success_message = (
        f"SSH key pair setup successfully. "
        f"Private key at: {cfg.ssh_key_path.as_posix()}"
    )

    utils.print_message_to_user(success_message)

    if log:
        utils.log(f"\n{success_message}")


def connect_client_with_logging(
    client: paramiko.SSHClient,
    cfg: Configs,
    password: Optional[str] = None,
    message_on_sucessful_connection: bool = True,
) -> None:
    """
    Connect client to central server using paramiko.
    Accept either password or path to private key, but not both.
    Paramiko does not support pathlib.
    """
    try:
        connect_client_core(client, cfg, password)
        if message_on_sucessful_connection:
            utils.print_message_to_user(
                f"Connection to { cfg['central_host_id']} made successfully."
            )

    except Exception:
        utils.log_and_raise_error(
            f"Could not connect to server. Ensure that \n"
            f"1) You have run setup_ssh_connection() \n"
            f"2) You are on VPN network if required. \n"
            f"3) The central_host_id: {cfg['central_host_id']} is"
            f" correct.\n"
            f"4) The central username:"
            f" {cfg['central_host_username']}, and password are correct.",
            ConnectionError,
        )


def verify_ssh_central_host(
    central_host_id: str, hostkeys_path: Path, log: bool = True
) -> bool:
    """
    Similar to connecting with other SSH manager e.g. putty,
    get the server key and present when connecting
    for manual validation.
    """
    key = get_remote_server_key(central_host_id)

    message = (
        f"The host key is not cached for this server: "
        f"{central_host_id}.\nYou have no guarantee "
        f"that the server is the computer you think it is.\n"
        f"The server's {key.get_name()} key fingerprint is: "
        f"{key.get_base64()}\nIf you trust this host, to connect"
        f" and cache the host key, press y: "
    )
    input_ = utils.get_user_input(message)

    if input_ == "y":
        save_hostkey_locally(key, central_host_id, hostkeys_path)
        success = True
        utils.print_message_to_user("Host accepted.")
    else:
        utils.print_message_to_user("Host not accepted. No connection made.")
        success = False

    if log:
        if success:
            utils.log(f"{message}")
            utils.log(f"Hostkeys saved at:{hostkeys_path.as_posix()}")
        else:
            utils.log("Host not accepted. No connection made.")

    return success


# -----------------------------------------------------------------------------
# Search over SSH
# -----------------------------------------------------------------------------


def search_ssh_central_for_folders(
    search_path: Path,
    search_prefix: str,
    cfg: Configs,
    verbose: bool = True,
    return_full_path: bool = False,
) -> Tuple[List[Any], List[Any]]:
    """
    Search for the search prefix in the search path over SSH.
    Returns the list of matching folders, files are filtered out.

    Parameters
    -----------

    search_path : path to search for folders in

    search_prefix : search prefix for folder names e.g. "sub-*"

    cfg : see connect_client_with_logging()

    verbose : If `True`, if a search folder cannot be found, a message
              will be printed with the un-found path.
    """
    client: paramiko.SSHClient
    with paramiko.SSHClient() as client:
        connect_client_with_logging(
            client, cfg, message_on_sucessful_connection=verbose
        )

        sftp = client.open_sftp()

        all_folder_names, all_filenames = get_list_of_folder_names_over_sftp(
            sftp,
            search_path,
            search_prefix,
            verbose,
            return_full_path,
        )

    return all_folder_names, all_filenames


def get_list_of_folder_names_over_sftp(
    sftp: paramiko.sftp_client.SFTPClient,
    search_path: Path,
    search_prefix: str,
    verbose: bool = True,
    return_full_path: bool = False,
) -> Tuple[List[Any], List[Any]]:
    """
    Use paramiko's sftp to search a path
    over ssh for folders. Return the folder names.

    Parameters
    ----------

    stfp : connected paramiko stfp object
        (see search_ssh_central_for_folders())

    search_path : path to search for folders in

    search_prefix : prefix (can include wildcards)
        to search folder names.

    verbose : If `True`, if a search folder cannot be found, a message
          will be printed with the un-found path.
    """
    all_folder_names = []
    all_filenames = []
    try:
        for file_or_folder in sftp.listdir_attr(search_path.as_posix()):

            if file_or_folder.st_mode is not None and fnmatch.fnmatch(
                file_or_folder.filename, search_prefix
            ):
                to_append = (
                    search_path / file_or_folder.filename
                    if return_full_path
                    else file_or_folder.filename
                )
                if stat.S_ISDIR(file_or_folder.st_mode):
                    all_folder_names.append(to_append)
                else:
                    all_filenames.append(to_append)

    except FileNotFoundError:
        if verbose:
            utils.log_and_message(f"No file found at {search_path.as_posix()}")

    return all_folder_names, all_filenames
