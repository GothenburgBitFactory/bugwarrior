from unittest import mock

import pytest

from bugwarrior.collect import TaskConstructor
from bugwarrior.services import bts

from .base import get_mock_service

SERVICE_CONFIG = {'service': 'bts', 'email': 'irl@debian.org', 'packages': 'bugwarrior'}


class FakeBTSBug:
    bug_num = 810629
    package = "wnpp"
    subject = (
        "ITP: bugwarrior -- Pull tickets from github, "
        "bitbucket, bugzilla, jira, trac, and others into "
        "taskwarrior"
    )
    severity = "wishlist"
    source = ""
    forwarded = ""
    pending = "pending"


class FakeBTSLib:
    def get_bugs(self, *args, **kwargs):
        return [810629]

    def get_status(self, bug_num):
        if bug_num == [810629]:
            return [FakeBTSBug]


class TestBTSService:
    @pytest.fixture
    def service(self):
        return get_mock_service(bts.BTSService, SERVICE_CONFIG)

    def test_to_taskwarrior(self, service):
        issue = service.get_issue_for_record(service._record_for_bug(FakeBTSBug))

        expected_output = {
            'priority': issue.PRIORITY_MAP[FakeBTSBug.severity],
            'annotations': [],
            issue.URL: "https://bugs.debian.org/" + str(FakeBTSBug.bug_num),
            issue.SUBJECT: FakeBTSBug.subject,
            issue.NUMBER: FakeBTSBug.bug_num,
            issue.PACKAGE: FakeBTSBug.package,
            issue.SOURCE: FakeBTSBug.source,
            issue.FORWARDED: FakeBTSBug.forwarded,
            issue.STATUS: FakeBTSBug.pending,
        }
        actual_output = issue.to_taskwarrior()

        assert actual_output == expected_output

    def test_issues(self, service):
        with mock.patch('bugwarrior.services.bts.debianbts', FakeBTSLib()):
            issue = next(service.issues())

        expected = {
            'annotations': [],
            'btsnumber': 810629,
            'btsforwarded': '',
            'btspackage': 'wnpp',
            'btssubject': (
                'ITP: bugwarrior -- Pull tickets from github, '
                'bitbucket, bugzilla, jira, trac, and others into '
                'taskwarrior'
            ),
            'btsurl': 'https://bugs.debian.org/810629',
            'btssource': '',
            'description': (
                '(bw)Is#810629 - ITP: bugwarrior -- Pull tickets fro .. '
                'https://bugs.debian.org/810629'
            ),
            'priority': 'L',
            'btsstatus': 'pending',
            'tags': [],
        }

        assert TaskConstructor(issue).get_taskwarrior_record() == expected
