import json

import pytest
import responses

from bugwarrior.collect import TaskConstructor
from bugwarrior.services.gerrit import GerritService

SERVICE_CLASS = GerritService

SERVICE_CONFIG = {
    "service": "gerrit",
    "base_uri": "https://one.com",
    "username": "two",
    "password": "three",
    "ignore_user_comments": ["CI Bot"],
}


@pytest.fixture
def record():
    return {
        "project": "nova",
        "_number": 1,
        "branch": "master",
        "topic": "test-topic",
        "status": "new",
        "work_in_progress": False,
        "subject": "this is a title",
        "messages": [
            {
                "author": {"username": "Iam Author"},
                "message": "this is a message",
                "_revision_number": 1,
            },
            {
                "author": {"username": "CI Bot"},
                "message": "ignore me please",
                "_revision_number": 1,
            },
        ],
    }


@pytest.fixture
def extra():
    return {
        "annotations": [
            # TODO - test annotations?
        ],
        "url": "https://one.com/#/c/1/",
    }


class TestGerritIssue:
    @pytest.fixture
    def service(self, make_service):
        # GerritService.__init__ sends a HEAD request to detect the server's
        # authentication method, so the responses mock must already be active
        # when the service is constructed, not just during the test.
        with responses.mock:
            responses.add(
                responses.HEAD,
                SERVICE_CONFIG["base_uri"] + "/a/",
                headers={"www-authenticate": "digest"},
            )
            return make_service()

    def test_to_taskwarrior(self, service, record, extra):
        issue = service.get_issue_for_record(record, extra)
        actual = issue.to_taskwarrior()
        expected = {
            "annotations": [],
            "priority": "M",
            "project": "nova",
            "gerritid": 1,
            "gerritstatus": "new",
            "gerritsummary": "this is a title",
            "gerriturl": "https://one.com/#/c/1/",
            "gerritbranch": "master",
            "gerrittopic": "test-topic",
            "gerritwip": 0,
            "tags": [],
        }

        assert actual == expected

    def test_work_in_progress(self, service, record, extra):
        record["work_in_progress"] = True
        issue = service.get_issue_for_record(record, extra)

        expected = {
            "annotations": [],
            "description": "(bw)PR#1 - this is a title .. https://one.com/#/c/1/",
            "gerritid": 1,
            "gerritsummary": "this is a title",
            "gerritstatus": "new",
            "gerriturl": "https://one.com/#/c/1/",
            "gerritbranch": "master",
            "gerrittopic": "test-topic",
            "gerritwip": 1,
            "priority": "M",
            "project": "nova",
            "tags": [],
        }

        assert TaskConstructor(issue).get_taskwarrior_record() == expected

    @responses.activate
    def test_issues(self, service, record):
        responses.get(
            "https://one.com/a/changes/?q=is:open+is:reviewer&o=MESSAGES&o=DETAILED_ACCOUNTS",
            # The response has some ")]}'" garbage prefixed.
            body=")]}'" + json.dumps([record]),
        )

        issue = next(service.issues())

        expected = {
            "annotations": ["@Iam Author - this is a message"],
            "description": "(bw)PR#1 - this is a title .. https://one.com/#/c/1/",
            "gerritid": 1,
            "gerritsummary": "this is a title",
            "gerritstatus": "new",
            "gerriturl": "https://one.com/#/c/1/",
            "gerritbranch": "master",
            "gerrittopic": "test-topic",
            "gerritwip": 0,
            "priority": "M",
            "project": "nova",
            "tags": [],
        }

        assert TaskConstructor(issue).get_taskwarrior_record() == expected
