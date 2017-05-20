from builtins import next
from builtins import object
from collections import namedtuple

import mock
from dateutil.tz import tzoffset, datetime

from bugwarrior.services.jira import JiraService
from .base import ServiceTest, AbstractServiceTest


class FakeJiraClient(object):
    def __init__(self, arbitrary_record):
        self.arbitrary_record = arbitrary_record

    def search_issues(self, *args, **kwargs):
        Case = namedtuple('Case', ['raw', 'key'])
        return [Case(self.arbitrary_record, self.arbitrary_record['key'])]

    def comments(self, *args, **kwargs):
        return None


class TestJiraIssue(AbstractServiceTest, ServiceTest):
    SERVICE_CONFIG = {
        'jira.username': 'one',
        'jira.base_uri': 'two',
        'jira.password': 'three',
    }

    arbitrary_estimation = 3600
    arbitrary_id = '10'
    arbitrary_project = 'DONUT'
    arbitrary_summary = 'lkjaldsfjaldf'

    arbitrary_record = {
        'fields': {
            'priority': 'Blocker',
            'summary': arbitrary_summary,
            'timeestimate': arbitrary_estimation,
            'created': '2016-06-06T06:07:08.123-0700',
            'fixVersions': [{'name': '1.2.3'}]
        },
        'key': '%s-%s' % (arbitrary_project, arbitrary_id, ),
    }

    def setUp(self):
        super(TestJiraIssue, self).setUp()
        with mock.patch('jira.client.JIRA._get_json'):
            self.service = self.get_mock_service(JiraService)

    def get_mock_service(self, *args, **kwargs):
        service = super(TestJiraIssue, self).get_mock_service(*args, **kwargs)
        service.jira = FakeJiraClient(self.arbitrary_record)
        return service

    def test_to_taskwarrior(self):
        arbitrary_url = 'http://one'
        arbitrary_extra = {
            'jira_version': 5,
            'annotations': ['an annotation'],
        }

        issue = self.service.get_issue_for_record(
            self.arbitrary_record, arbitrary_extra
        )

        expected_output = {
            'project': self.arbitrary_project,
            'priority': (
                issue.PRIORITY_MAP[self.arbitrary_record['fields']['priority']]
            ),
            'annotations': arbitrary_extra['annotations'],
            'tags': [],
            'entry': datetime.datetime(2016, 6, 6, 6, 7, 8, 123000, tzinfo=tzoffset(None, -25200)),
            'jirafixversion': '1.2.3',

            issue.URL: arbitrary_url,
            issue.FOREIGN_ID: self.arbitrary_record['key'],
            issue.SUMMARY: self.arbitrary_summary,
            issue.DESCRIPTION: None,
            issue.ESTIMATE: self.arbitrary_estimation / 60 / 60
        }

        def get_url(*args):
            return arbitrary_url

        with mock.patch.object(issue, 'get_url', side_effect=get_url):
            actual_output = issue.to_taskwarrior()

        self.assertEqual(actual_output, expected_output)

    def test_issues(self):
        issue = next(self.service.issues())

        expected = {
            'annotations': [],
            'description': '(bw)Is#10 - lkjaldsfjaldf .. two/browse/DONUT-10',
            'entry': datetime.datetime(2016, 6, 6, 6, 7, 8, 123000, tzinfo=tzoffset(None, -25200)),
            'jiradescription': None,
            'jiraestimate': 1,
            'jirafixversion': '1.2.3',
            'jiraid': 'DONUT-10',
            'jirasummary': 'lkjaldsfjaldf',
            'jiraurl': 'two/browse/DONUT-10',
            'priority': 'H',
            'project': 'DONUT',
            'tags': []}

        self.assertEqual(issue.get_taskwarrior_record(), expected)
