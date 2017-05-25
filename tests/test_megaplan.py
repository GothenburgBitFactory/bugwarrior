from builtins import next
from builtins import object
import mock
import unittest

try:
    from bugwarrior.services.mplan import MegaplanService
except SyntaxError:
    raise unittest.SkipTest(
        'Upstream python-megaplan does not support python3 yet.')

from .base import ServiceTest, AbstractServiceTest


class FakeMegaplanClient(object):
    def __init__(self, record):
        self.record = record
    def get_actual_tasks(self):
        return [self.record]


class TestMegaplanIssue(AbstractServiceTest, ServiceTest):
    SERVICE_CONFIG = {
        'megaplan.hostname': 'something',
        'megaplan.login': 'something_else',
        'megaplan.password': 'aljlkj',
    }
    name_parts = ['one', 'two', 'three']
    arbitrary_issue = {
        'Id': 10,
        'Name': '|'.join(name_parts)
    }

    def setUp(self):
        super(TestMegaplanIssue, self).setUp()
        with mock.patch('megaplan.Client'):
            self.service = self.get_mock_service(MegaplanService)

    def get_mock_service(self, *args, **kwargs):
        service = super(TestMegaplanIssue, self).get_mock_service(
            *args, **kwargs)
        service.client = FakeMegaplanClient(self.arbitrary_issue)
        return service

    def test_to_taskwarrior(self):
        arbitrary_project = 'one'
        arbitrary_url = 'http://one.com/'

        issue = self.service.get_issue_for_record(self.arbitrary_issue)

        expected_output = {
            'project': arbitrary_project,
            'priority': self.service.default_priority,

            issue.FOREIGN_ID: self.arbitrary_issue['Id'],
            issue.URL: arbitrary_url,
            issue.TITLE: self.name_parts[-1]
        }

        def get_url(*args):
            return arbitrary_url

        def get_project(*args):
            return arbitrary_project

        with mock.patch.multiple(
            issue, get_project=mock.DEFAULT, get_issue_url=mock.DEFAULT
        ) as mocked:
            mocked['get_project'].side_effect = get_project
            mocked['get_issue_url'].side_effect = get_url
            actual_output = issue.to_taskwarrior()

        self.assertEqual(actual_output, expected_output)

    def test_issues(self):
        issue = next(self.service.issues())

        expected = {
            'description':
                '(bw)Is#10 - three .. https://something/task/10/card/',
            'megaplanid': 10,
            'megaplantitle': 'three',
            'megaplanurl': 'https://something/task/10/card/',
            'priority': 'M',
            'project': 'something',
            'tags': []}

        self.assertEqual(issue.get_taskwarrior_record(), expected)
