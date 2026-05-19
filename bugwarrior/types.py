from typing import Any, NamedTuple

TaskwarriorData = dict[str, Any]


class CollectedIssue(NamedTuple):
    taskwarrior_data: TaskwarriorData
    target: str
    identifier: str


class CollectionErrorData(NamedTuple):
    error_message: str
    target: str
