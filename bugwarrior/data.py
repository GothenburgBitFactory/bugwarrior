import os
import json

from lockfile.pidlockfile import PIDLockFile

from bugwarrior.config import get_data_path


DATAFILE = os.path.join(get_data_path(), 'bugwarrior.data')
LOCKFILE = os.path.join(get_data_path(), 'bugwarrior-data.lockfile')


def get(key):
    try:
        with open(DATAFILE, 'r') as jsondata:
            try:
                data = json.load(jsondata)
            except ValueError:  # File does not contain JSON.
                return None
            else:
                return data[key]
    except IOError:  # File does not exist.
        return None


def set(key, value):
    with PIDLockFile(LOCKFILE):
        try:
            with open(DATAFILE, 'r+') as jsondata:
                data = json.load(jsondata)
                data[key] = value
                json.dump(data, jsondata)
        except IOError:  # File does not exist.
            with open(DATAFILE, 'w+') as jsondata:
                json.dump({key: value}, jsondata)
