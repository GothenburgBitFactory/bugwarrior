import json
import os
import subprocess

from lockfile.pidlockfile import PIDLockFile


def get_data_path(taskrc):
    # We cannot use the taskw module here because it doesn't really support
    # the `_` subcommands properly (`rc:` can't be used for them).
    line_prefix = 'data.location='

    # Take a copy of the environment and add our taskrc to it.
    env = dict(os.environ)
    env['TASKRC'] = taskrc

    tw_show = subprocess.Popen(
        ('task', '_show'), stdout=subprocess.PIPE, env=env)
    data_location = subprocess.check_output(
        ('grep', '-e', '^' + line_prefix), stdin=tw_show.stdout)
    tw_show.wait()
    data_path = data_location[len(line_prefix):].rstrip().decode('utf-8')

    if not data_path:
        raise OSError('Unable to determine the data location.')

    return os.path.normpath(os.path.expanduser(data_path))


class BugwarriorData:
    def __init__(self, data_path):
        self.datafile = os.path.join(data_path, 'bugwarrior.data')
        self.lockfile = os.path.join(data_path, 'bugwarrior-data.lockfile')
        self.path = data_path

    def get_data(self):
        with open(self.datafile) as jsondata:
            return json.load(jsondata)

    def get(self, key):
        try:
            return self.get_data()[key]
        except OSError:  # File does not exist.
            return None

    def set(self, key, value):
        with PIDLockFile(self.lockfile):
            try:
                data = self.get_data()
            except OSError:  # File does not exist.
                with open(self.datafile, 'w') as jsondata:
                    json.dump({key: value}, jsondata)
            else:
                with open(self.datafile, 'w') as jsondata:
                    data[key] = value
                    json.dump(data, jsondata)

            os.chmod(self.datafile, 0o600)
