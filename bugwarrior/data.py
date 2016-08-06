import os
import json

from lockfile.pidlockfile import PIDLockFile

from bugwarrior.config import get_data_path


class BugwarriorData(object):
    def __init__(self, config, main_section):
        data_path = get_data_path(config, main_section)
        self.datafile = os.path.join(data_path, 'bugwarrior.data')
        self.lockfile = os.path.join(data_path, 'bugwarrior-data.lockfile')

    def get(self, key):
        try:
            with open(self.datafile, 'r') as jsondata:
                try:
                    data = json.load(jsondata)
                except ValueError:  # File does not contain JSON.
                    return None
                else:
                    return data[key]
        except IOError:  # File does not exist.
            return None

    def set(self, key, value):
        with PIDLockFile(self.lockfile):
            try:
                with open(self.datafile, 'r+') as jsondata:
                    data = json.load(jsondata)
                    data[key] = value
                    json.dump(data, jsondata)
            except IOError:  # File does not exist.
                with open(self.datafile, 'w+') as jsondata:
                    json.dump({key: value}, jsondata)
