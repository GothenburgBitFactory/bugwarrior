import os

from twiggy import log
from lockfile import LockTimeout
from lockfile.pidlockfile import PIDLockFile

import twiggy
import getpass
import keyring
import click

from taskw.warrior import TaskWarriorBase

from bugwarrior.config import get_taskrc_path, load_config
from bugwarrior.services import aggregate_issues, SERVICES
from bugwarrior.db import (
    get_defined_udas_as_strings,
    synchronize,
)


# We overwrite 'list' further down.
lst = list


def _get_section_name(flavor):
    if flavor:
        return 'flavor.' + flavor
    return 'general'


@click.command()
@click.option('--dry-run', is_flag=True)
@click.option('--flavor', default=None, help='The flavor to use')
def pull(dry_run, flavor):
    """ Pull down tasks from forges and add them to your taskwarrior tasks.

    Relies on configuration in bugwarriorrc
    """
    twiggy.quickSetup()
    try:
        main_section = _get_section_name(flavor)

        # Load our config file
        config = load_config(main_section)

        tw_config = TaskWarriorBase.load_config(get_taskrc_path(config, main_section))
        lockfile_path = os.path.join(
            os.path.expanduser(
                tw_config['data']['location']
            ),
            'bugwarrior.lockfile'
        )

        lockfile = PIDLockFile(lockfile_path)
        lockfile.acquire(timeout=10)
        try:
            # Get all the issues.  This can take a while.
            issue_generator = aggregate_issues(config, main_section)

            # Stuff them in the taskwarrior db as necessary
            synchronize(issue_generator, config, main_section, dry_run)
        finally:
            lockfile.release()
    except LockTimeout:
        log.name('command').critical(
            'Your taskrc repository is currently locked. '
            'Remove the file at %s if you are sure no other '
            'bugwarrior processes are currently running.' % (
                lockfile_path
            )
        )
    except:
        log.name('command').trace('error').critical('oh noes')


@click.group()
def vault():
    """ Password/keyring management for bugwarrior.

    If you use the keyring password oracle in your bugwarrior config, this tool
    can be used to manage your keyring.
    """
    pass


def targets():
    config = load_config('general')
    for section in config.sections():
        if section in ['general', 'notifications'] or \
           section.startswith('flavor.'):
            continue
        service_name = config.get(section, 'service')
        service_class = SERVICES[service_name]
        for option in config.options(section):
            value = config.get(section, option)
            if not value:
                continue
            if '@oracle:use_keyring' in value:
                yield service_class.get_keyring_service(config, section)


@vault.command()
def list():
    pws = lst(targets())
    print "%i @oracle:use_keyring passwords in bugwarriorrc" % len(pws)
    for section in pws:
        print "-", section


@vault.command()
@click.argument('target')
@click.argument('username')
def clear(target, username):
    target_list = lst(targets())
    if target not in target_list:
        raise ValueError("%s must be one of %r" % (target, target_list))

    if keyring.get_password(target, username):
        keyring.delete_password(target, username)
        print "Password cleared for %s, %s" % (target, username)
    else:
        print "No password found for %s, %s" % (target, username)


@vault.command()
@click.argument('target')
@click.argument('username')
def set(target, username):
    target_list = lst(targets())
    if target not in target_list:
        raise ValueError("%s must be one of %r" % (target, target_list))

    keyring.set_password(target, username, getpass.getpass())
    print "Password set for %s, %s" % (target, username)


@click.command()
@click.option('--flavor', default=None, help='The flavor to use')
def uda(flavor):
    main_section = _get_section_name(flavor)
    conf = load_config(main_section)
    print "# Bugwarrior UDAs"
    for uda in get_defined_udas_as_strings(conf, main_section):
        print uda
    print "# END Bugwarrior UDAs"
