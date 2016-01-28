import os
import json


DATAFILE = os.path.expanduser(
    os.path.join(os.getenv('TASKDATA', '~/.task'), 'bugwarrior.data'))


def get(key):
    try:
        with open(DATAFILE, 'r') as jsondata:
            data = json.load(jsondata)
            return data[key]
    except IOError:  # File does not exist.
        return None


def set(key, value):
    try:
        with open(DATAFILE, 'rw') as jsondata:
            data = json.load(jsondata)
            data[key] = value
            json.dump(data, jsondata)
    except IOError:  # File does not exist.
        with open(DATAFILE, 'w+') as jsondata:
            json.dump({key: value}, jsondata)
