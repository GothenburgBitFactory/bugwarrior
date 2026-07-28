from collections.abc import Callable, Iterator
import functools
import getpass
import logging
import os
import sys
from typing import TYPE_CHECKING, Any
import warnings

import click
from filelock import FileLock, Timeout

from bugwarrior.collect import aggregate_issues
from bugwarrior.config import get_config_path, get_keyring, load_config
from bugwarrior.db import get_defined_udas_as_strings, synchronize

if TYPE_CHECKING:
    from bugwarrior.config.validation import Config
log = logging.getLogger(__name__)


# We overwrite 'list' further down.
lst = list


def _get_section_name(flavor: str | None) -> str:
    if flavor:
        return 'flavor.' + flavor
    return 'general'


def _try_load_config(main_section: str, quiet: bool = False) -> "Config":
    try:
        return load_config(main_section, quiet)
    except OSError:
        # Our standard logging configuration depends on the bugwarrior
        # configuration file which just failed to load.
        logging.basicConfig()

        log.critical(
            "Could not load configuration. "
            "Maybe you have not created a configuration file.",
            exc_info=True,
        )
        sys.exit(1)


def _legacy_cli_deprecation_warning(
    subcommand_callback: Callable[..., Any],
) -> Callable[..., Any]:
    @functools.wraps(subcommand_callback)
    @click.pass_context
    def wrapped_subcommand_callback(
        ctx: click.Context, *args: Any, **kwargs: Any
    ) -> Any:
        if ctx.find_root().command_path != 'bugwarrior':
            old_command = ctx.command_path
            new_command = ctx.command_path.replace('-', ' ')
            log.warning(
                f'Deprecation Warning: `{old_command}` is deprecated and will '
                'be removed in a future version of bugwarrior. Please use '
                f'`{new_command}` instead.'
            )
        return ctx.invoke(subcommand_callback, *args, **kwargs)

    return wrapped_subcommand_callback


class AliasedCli(click.Group):
    """
    Integrates subcommands into a top-level bugwarrior command.

    By implementing this as an alias, we can maintain backwards compatibility
    with the old cli api.
    """

    def list_commands(self, ctx: click.Context) -> list[str]:
        assert isinstance(ctx.command, click.Group)
        return list(ctx.command.commands)

    def get_command(self, ctx: click.Context, cmd_name: str) -> click.Command | None:
        assert isinstance(ctx.command, click.Group)
        return ctx.command.commands.get(cmd_name)


@click.command(cls=AliasedCli)
@click.version_option()
def cli() -> None:
    pass


@cli.command()
@click.option('--dry-run', is_flag=True)
@click.option('--flavor', default=None, help='The flavor to use')
@click.option(
    '--interactive',
    is_flag=True,
    help='Deprecated. Interactive mode is now detected automatically via isatty().',
)
@click.option(
    '--debug', is_flag=True, help='Do not use multiprocessing (which breaks pdb).'
)
@click.option('--quiet', is_flag=True, help='Set logging level to WARNING.')
@_legacy_cli_deprecation_warning
def pull(
    dry_run: bool, flavor: str | None, interactive: bool, debug: bool, quiet: bool
) -> None:
    """Pull down tasks from forges and add them to your taskwarrior tasks.

    Relies on configuration file.
    """
    if interactive:
        warnings.warn(
            "The --interactive flag is deprecated and has no effect. "
            "Interactive mode is now detected automatically via sys.stdin.isatty().",
            DeprecationWarning,
            stacklevel=2,
        )

    try:
        main_section = _get_section_name(flavor)
        config = _try_load_config(main_section, quiet)

        lockfile_path = os.path.join(config.main.data.path, 'bugwarrior.lockfile')
        with FileLock(lockfile_path, timeout=10):
            # Get all the issues.  This can take a while.
            issue_generator = aggregate_issues(config, debug)

            # Stuff them in the taskwarrior db as necessary
            synchronize(issue_generator, config, dry_run)
    except Timeout:
        log.critical(
            'Your taskrc repository is currently locked. '
            'Wait for any running bugwarrior processes to finish and try again. '
            f'Lock file:{lockfile_path}'
        )
        sys.exit(1)
    except RuntimeError as e:
        log.exception("Aborted (%s)" % e)
        sys.exit(1)


@cli.group()
@_legacy_cli_deprecation_warning
def vault() -> None:
    """Password/keyring management for bugwarrior.

    If you use the keyring password oracle in your bugwarrior config, this tool
    can be used to manage your keyring. This feature requires the optional
    keyring library. (pip install "bugwarrior[keyring]")
    """


def targets() -> Iterator[str]:
    config = _try_load_config('general')
    for service_config in config.service_configs:
        for value in dict(service_config).values():
            if isinstance(value, str) and '@oracle:use_keyring' in value:
                yield service_config.keyring_service


@vault.command()
def list() -> None:
    pws = lst(targets())
    print("%i @oracle:use_keyring passwords in bugwarriorrc" % len(pws))
    for section in pws:
        print("-", section)


@vault.command()
@click.argument('target')
@click.argument('username')
def clear(target: str, username: str) -> None:
    target_list = lst(targets())
    if target not in target_list:
        raise ValueError("%s must be one of %r" % (target, target_list))

    keyring = get_keyring()
    if keyring.get_password(target, username):
        keyring.delete_password(target, username)
        print("Password cleared for %s, %s" % (target, username))
    else:
        print("No password found for %s, %s" % (target, username))


@vault.command()
@click.argument('target')
@click.argument('username')
def set(target: str, username: str) -> None:
    target_list = lst(targets())
    if target not in target_list:
        log.warning(
            "You must configure the password to '@oracle:use_keyring' "
            "prior to setting the value."
        )
        raise ValueError("%s must be one of %r" % (target, target_list))

    keyring = get_keyring()
    keyring.set_password(target, username, getpass.getpass())
    print("Password set for %s, %s" % (target, username))


@cli.command()
@click.option('--flavor', default=None, help='The flavor to use')
@_legacy_cli_deprecation_warning
def uda(flavor: str | None) -> None:
    """
    List bugwarrior-managed uda's.

    Most services define a set of UDAs in which bugwarrior store extra information
    about the incoming ticket.  Usually, this includes things like the title
    of the ticket and its URL, but some services provide an extensive amount of
    metadata.  See each service's documentation for more information.

    For using this data in reports, it is recommended that you add these UDA
    definitions to your ``taskrc`` file. You can add the output of this command
    verbatim to your ``taskrc`` file if you would like Taskwarrior to know the
    human-readable name and data type for the defined UDAs.

    .. note::

       Not adding those lines to your ``taskrc`` file will have no negative
       effects aside from Taskwarrior not knowing the human-readable name for the
       field, but depending on what version of Taskwarrior you are using, it
       may prevent you from changing the values of those fields or using them
       in filter expressions.
    """
    main_section = _get_section_name(flavor)
    conf = _try_load_config(main_section)
    print("# Bugwarrior UDAs")
    for uda in get_defined_udas_as_strings(conf):
        print(uda)
    print("# END Bugwarrior UDAs")


@cli.command()
@click.argument(
    'rcfile', required=False, default=get_config_path(), type=click.Path(exists=True)
)
def ini2toml(rcfile: str) -> None:
    """Convert ini bugwarriorrc to toml and print result to stdout."""
    try:
        from ini2toml.api import Translator
    except ImportError:
        raise SystemExit(
            'Install extra dependencies to use this command:\n'
            '    pip install bugwarrior[ini2toml]'
        )
    if os.path.splitext(rcfile)[-1] == '.toml':
        raise SystemExit(f'{rcfile} is already toml!')
    with open(rcfile, 'r') as f:
        bugwarriorrc = f.read()
    print(Translator().translate(bugwarriorrc, 'bugwarriorrc'))
