import json
import os
import subprocess
import typing

from lockfile.pidlockfile import PIDLockFile


def get_data_path(taskrc):
    # We cannot use the taskw module here because it doesn't really support
    # the `_` subcommands properly (`rc:` can't be used for them).
    line_prefix = 'data.location='

    # Take a copy of the environment and add our taskrc to it.
    env = dict(os.environ)
    env['TASKRC'] = taskrc

    tw_show = subprocess.Popen(('task', '_show'), stdout=subprocess.PIPE, env=env)
    data_location = subprocess.check_output(
        ('grep', '-e', '^' + line_prefix), stdin=tw_show.stdout
    )
    tw_show.wait()
    data_path = data_location[len(line_prefix) :].rstrip().decode('utf-8')

    if not data_path:
        raise OSError('Unable to determine the data location.')

    return os.path.normpath(os.path.expanduser(data_path))


class BugwarriorData:
    """Local data storage.

    This exposes taskwarrior's `data.location` configuration value, as well as
    an interface to the ``bugwarrior.data`` file which serves as an arbitrary
    key-value store.
    """

    def __init__(self, data_path):
        self._datafile = os.path.join(data_path, 'bugwarrior.data')
        self._lockfile = os.path.join(data_path, 'bugwarrior-data.lockfile')
        #: Taskwarrior's ``data.location`` configuration value. If necessary,
        #: services can manage their own files here.
        self.path = data_path

    @classmethod
    def __get_pydantic_json_schema__(cls, core_schema, handler):
        """Fix schema generation in pydantic v2."""
        return {"type": "object", "description": "Local data storage"}

    def get_data(self) -> dict:
        """Return all data from the ``bugwarrior.data`` file."""
        with open(self._datafile) as jsondata:
            return json.load(jsondata)

    def get(self, key) -> typing.Any:
        """Return a value stored in the ``bugwarrior.data`` file."""
        try:
            return self.get_data()[key]
        except OSError:  # File does not exist.
            return None

    def set(self, key, value):
        """Set a value in the ``bugwarrior.data`` file."""
        with PIDLockFile(self._lockfile):
            try:
                data = self.get_data()
            except OSError:  # File does not exist.
                with open(self._datafile, 'w') as jsondata:
                    json.dump({key: value}, jsondata)
            else:
                with open(self._datafile, 'w') as jsondata:
                    data[key] = value
                    json.dump(data, jsondata)

            os.chmod(self._datafile, 0o600)
