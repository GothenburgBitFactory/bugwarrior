import os

from twiggy import log
from lockfile import LockTimeout
from lockfile.pidlockfile import PIDLockFile

from taskw.warrior import TaskWarriorBase

from bugwarrior.config import get_taskrc_path, load_config
from bugwarrior.services import aggregate_issues
from bugwarrior.db import synchronize


def pull():
    try:
        # Load our config file
        config = load_config()

        tw_config = TaskWarriorBase.load_config(get_taskrc_path(config))
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
            issue_generator = aggregate_issues(config)

            # Stuff them in the taskwarrior db as necessary
            synchronize(issue_generator, config)
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
