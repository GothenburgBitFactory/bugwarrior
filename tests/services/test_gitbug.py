from datetime import datetime, timedelta, timezone
from unittest import mock

import pytest

from bugwarrior.collect import TaskConstructor
from bugwarrior.services.gitbug import GitBugClient, GitBugConfig, GitBugService


@pytest.fixture
def record():
    return {
        "author": {"name": "ryneeverett"},
        "comments": {
            "nodes": [
                {
                    "author": {"name": "ryneeverett"},
                    "message": "This is the description, albeit a brief one.",
                }
            ]
        },
        "createdAt": "2022-05-05T23:06:52-04:00",
        "id": "032d911695cc68d9881aabc24a6c62853f90f834",
        "labels": [],
        "status": "OPEN",
        "title": "Some Issue",
    }


SERVICE_CLASS = GitBugService

SERVICE_CONFIG = {"service": "gitbug", "path": "/dev/null"}


class TestGitBugIssue:
    @pytest.fixture
    def service(self, record, make_service):
        service = make_service()
        service.client = mock.MagicMock(spec=GitBugClient)
        service.client.get_issues = mock.MagicMock(return_value=[record])
        return service

    def test_to_taskwarrior(self, service, record):
        issue = service.get_issue_for_record(record, {})

        expected = {
            "annotations": [],
            "entry": datetime(
                2022, 5, 5, 23, 6, 52, tzinfo=timezone(timedelta(seconds=-14400))
            ),
            "gitbugauthor": "ryneeverett",
            "gitbugid": "032d911695cc68d9881aabc24a6c62853f90f834",
            "gitbugstate": "OPEN",
            "gitbugtitle": "Some Issue",
            "priority": "M",
            "project": "unspecified",
            "tags": [],
        }
        actual = issue.to_taskwarrior()

        assert actual == expected

    def test_issues(self, service):
        issue = next(service.issues())

        expected = {
            "annotations": [],
            "description": "(bw)Bug# - Some Issue",
            "entry": datetime(
                2022, 5, 5, 23, 6, 52, tzinfo=timezone(timedelta(seconds=-14400))
            ),
            "gitbugauthor": "ryneeverett",
            "gitbugid": "032d911695cc68d9881aabc24a6c62853f90f834",
            "gitbugstate": "OPEN",
            "gitbugtitle": "Some Issue",
            "priority": "M",
            "project": "unspecified",
            "tags": [],
        }

        assert TaskConstructor(issue).get_taskwarrior_record() == expected


def test_home_path_expansion(tmp_path):
    # The path field is an ExpandedPath, so a configured tilde expands to the
    # user's home, which the autouse config_environment fixture points at
    # tmp_path.
    config = GitBugConfig(
        service="gitbug", path="~/custom-gitbug-repo", target="mygitbug"
    )
    assert config.path == tmp_path / "custom-gitbug-repo"
