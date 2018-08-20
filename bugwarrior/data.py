import os
import json

from lockfile.pidlockfile import PIDLockFile


class BugwarriorData(object):
    def __init__(self, data_path):
        self.datafile = os.path.join(data_path, 'bugwarrior.data')
        self.lockfile = os.path.join(data_path, 'bugwarrior-data.lockfile')
        self.path = data_path

    def get_data(self):
        with open(self.datafile, 'r') as jsondata:
            return json.load(jsondata)

    def get(self, key):
        try:
            return self.get_data()[key]
        except IOError:  # File does not exist.
            return None

    def set(self, key, value):
        with PIDLockFile(self.lockfile):
            try:
                data = self.get_data()
            except IOError:  # File does not exist.
                with open(self.datafile, 'w') as jsondata:
                    json.dump({key: value}, jsondata)
            else:
                with open(self.datafile, 'w') as jsondata:
                    data[key] = value
                    json.dump(data, jsondata)

            os.chmod(self.datafile, 0o600)
