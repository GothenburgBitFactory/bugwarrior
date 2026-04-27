import getpass
import logging
import subprocess
import sys
from types import ModuleType

log = logging.getLogger(__name__)


def get_keyring() -> ModuleType:
    """Try to import and return optional keyring dependency."""
    try:
        import keyring
    except ImportError:
        raise ImportError(
            "Extra dependencies must be installed to use the keyring feature. "
            "Install them with `pip install bugwarrior[keyring]`."
        )
    return keyring


def _ask_password(service: str) -> str:
    if not sys.stdin.isatty():
        log.error(
            f"Unable to retrieve password for service {service}. "
            "Not running in an interactive terminal; cannot prompt for password."
        )
        sys.exit(1)

    return getpass.getpass(f"{service} password: ")


def get_service_password(service: str, username: str, oracle: str | None = None) -> str:
    """
    Retrieve the sensitive password for a service by:

      * retrieving password from a secure store (@oracle:use_keyring, default)
      * asking the password from the user (@oracle:ask_password, interactive)
      * executing a command and use the output as password
        (@oracle:eval:<command>)

    Note that the keyring may or may not be locked
    which requires that the user provides a password (interactive mode).
    Interactive mode is detected automatically via sys.stdin.isatty().

    .. seealso::
        https://bitbucket.org/kang/python-keyring-lib
    """

    oracle = oracle.removeprefix("@oracle:") if oracle else "use_keyring"

    match oracle:
        case "ask_password":
            return _ask_password(service)

        case "use_keyring":
            keyring = get_keyring()
            try:
                password = keyring.get_password(service, username)
            except keyring.errors.KeyringLocked:
                # keyring unlocking failed.
                # TODO we should probably have a timeout, otherwise the dialog could block
                log.error(
                    f"Keyring is locked for service {service}. "
                    "Unlock your keyring and try again."
                )
                sys.exit(1)

            if password is not None:
                return password

            # LEARNING MODE: password not in keyring yet, prompt and store it.
            log.info(
                f"password for {service} is not in keyring, trying to ask for new password"
            )
            password = _ask_password(service)
            keyring.set_password(service, username, password)
            return password

        case _:
            if not oracle.startswith("eval:"):
                log.error(f"Unknown oracle for service {service}: {oracle}")
                sys.exit(1)

            return oracle_eval(oracle.removeprefix("eval:"))


def oracle_eval(command: str) -> str:
    """Retrieve password from the given command"""
    p = subprocess.Popen(
        command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    p.wait()
    assert p.stdout is not None
    assert p.stderr is not None
    if p.returncode == 0:
        return p.stdout.readline().strip().decode('utf-8')
    else:
        log.critical(
            "Error retrieving password: `{command}` returned '{error}'".format(
                command=command, error=p.stderr.read().strip()
            )
        )
        sys.exit(1)
