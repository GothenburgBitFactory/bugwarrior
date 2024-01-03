import dataclasses
import datetime
from unittest import mock

import dateutil

from bugwarrior.collect import TaskConstructor
from bugwarrior.services.gitbug import GitBugClient, GitBugConfig, GitBugService

from .base import AbstractServiceTest, ConfigTest, ServiceTest


@dataclasses.dataclass
class TestData:
    arbitrary_bug = {
        'author': {'name': 'ryneeverett'},
        'comments': {
            'nodes': [
                {'author': {'name': 'ryneeverett'},
                 'message': 'This is the description, albeit a brief one.'}
            ]},
        'createdAt': '2022-05-05T23:06:52-04:00',
        'id': '032d911695cc68d9881aabc24a6c62853f90f834',
        'labels': [],
        'status': 'OPEN',
        'title': 'Some Issue'
    }


class TestGitBugIssue(AbstractServiceTest, ServiceTest):
    SERVICE_CONFIG = {
        'service': 'gitbug',
        'path': '/dev/null',
    }

    def setUp(self):
        super().setUp()

        self.data = TestData()

        self.service = self.get_mock_service(GitBugService)
        self.service.client = mock.MagicMock(spec=GitBugClient)
        self.service.client.get_issues = mock.MagicMock(
            return_value=[self.data.arbitrary_bug])

    def test_to_taskwarrior(self):
        issue = self.service.get_issue_for_record(
            self.data.arbitrary_bug, {})

        expected = {
            'annotations': [],
            'entry': datetime.datetime(
                2022, 5, 5, 23, 6, 52,
                tzinfo=dateutil.tz.tzoffset(None, -14400)),
            'gitbugauthor': 'ryneeverett',
            'gitbugid': '032d911695cc68d9881aabc24a6c62853f90f834',
            'gitbugstate': 'OPEN',
            'gitbugtitle': 'Some Issue',
            'priority': 'M',
            'project': 'unspecified',
            'tags': []
        }
        actual = issue.to_taskwarrior()

        self.assertEqual(actual, expected)

    def test_issues(self):
        issue = next(self.service.issues())

        expected = {
            'annotations': [],
            'description': '(bw)Bug# - Some Issue',
            'entry': datetime.datetime(
                2022, 5, 5, 23, 6, 52,
                tzinfo=dateutil.tz.tzoffset(None, -14400)),
            'gitbugauthor': 'ryneeverett',
            'gitbugid': '032d911695cc68d9881aabc24a6c62853f90f834',
            'gitbugstate': 'OPEN',
            'gitbugtitle': 'Some Issue',
            'priority': 'M',
            'project': 'unspecified',
            'tags': []
        }

        self.assertEqual(TaskConstructor(issue).get_taskwarrior_record(), expected)


class TestGitBugConfig(ConfigTest):
    def setUp(self):
        super().setUp()
        self.config = GitBugConfig(service="gitbug", path="~/custom-gitbug-repo")

    def test_home_path_expansion(self):
        expected = self.tempdir + "/custom-gitbug-repo"
        self.assertEqual(self.config.path, expected)
