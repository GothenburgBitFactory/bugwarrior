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

    :param service:     Service name, may be key into secure store (as string).
    :param username:    Username for the service (as string).
    :param oracle:      Hint which password oracle strategy to use.
    :return: Retrieved password (as string)

    .. seealso::
        https://bitbucket.org/kang/python-keyring-lib
    """
    import getpass

    interactive = sys.stdin.isatty()
    password = None
    if not oracle or oracle == "@oracle:use_keyring":
        keyring = get_keyring()
        password = keyring.get_password(service, username)
        if interactive and password is None:
            # -- LEARNING MODE: Password is not stored in keyring yet.
            oracle = "@oracle:ask_password"
            password = get_service_password(service, username, oracle)
            if password:
                keyring.set_password(service, username, password)
        elif not interactive and password is None:
            log.error(
                'Unable to retrieve password from keyring. '
                'Not running in an interactive terminal; cannot prompt for password.'
            )
    elif interactive and oracle == "@oracle:ask_password":
        prompt = "%s password: " % service
        password = getpass.getpass(prompt)
    elif oracle.startswith('@oracle:eval:'):
        command = oracle[13:]
        return oracle_eval(command)

    if password is None:
        log.critical(
            "MISSING PASSWORD: oracle='%s', interactive=%s for service=%s"
            % (oracle, sys.stdin.isatty(), service)
        )
        sys.exit(1)
    return password


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
