import os
import json

from lockfile.pidlockfile import PIDLockFile

from bugwarrior.config import get_data_path


def datafile():
    return os.path.join(get_data_path(), 'bugwarrior.data')

def lockfile():
    return os.path.join(get_data_path(), 'bugwarrior-data.lockfile')


def get(key):
    try:
        with open(datafile(), 'r') as jsondata:
            try:
                data = json.load(jsondata)
            except ValueError:  # File does not contain JSON.
                return None
            else:
                return data[key]
    except IOError:  # File does not exist.
        return None


def set(key, value):
    with PIDLockFile(lockfile()):
        try:
            with open(datafile(), 'r+') as jsondata:
                data = json.load(jsondata)
                data[key] = value
                json.dump(data, jsondata)
        except IOError:  # File does not exist.
            with open(datafile(), 'w+') as jsondata:
                json.dump({key: value}, jsondata)
