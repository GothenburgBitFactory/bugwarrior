from builtins import next
from builtins import object
import mock
from collections import namedtuple

from bugwarrior.services.bz import BugzillaService

from .base import ServiceTest, AbstractServiceTest


class FakeBugzillaLib(object):
    def __init__(self, record):
        self.record = record

    def query(self, query):
        Record = namedtuple('Record', list(self.record.keys()))
        return [Record(**self.record)]


class TestBugzillaService(AbstractServiceTest, ServiceTest):
    SERVICE_CONFIG = {
        'bugzilla.base_uri': 'http://one.com/',
        'bugzilla.username': 'hello',
        'bugzilla.password': 'there',
    }

    arbitrary_record = {
        'component': 'Something',
        'priority': 'urgent',
        'status': 'NEW',
        'summary': 'This is the issue summary',
        'id': 1234567,
        'flags': [],
    }

    def setUp(self):
        with mock.patch('bugzilla.Bugzilla'):
            self.service = self.get_mock_service(BugzillaService)

    def get_mock_service(self, *args, **kwargs):
        service = super(TestBugzillaService, self).get_mock_service(
            *args, **kwargs)
        service.bz = FakeBugzillaLib(self.arbitrary_record)
        return service

    def test_to_taskwarrior(self):
        arbitrary_extra = {
            'url': 'http://path/to/issue/',
            'annotations': [
                'Two',
            ],
        }

        issue = self.service.get_issue_for_record(
            self.arbitrary_record,
            arbitrary_extra,
        )

        expected_output = {
            'project': self.arbitrary_record['component'],
            'priority': issue.PRIORITY_MAP[self.arbitrary_record['priority']],
            'annotations': arbitrary_extra['annotations'],

            issue.STATUS: self.arbitrary_record['status'],
            issue.URL: arbitrary_extra['url'],
            issue.SUMMARY: self.arbitrary_record['summary'],
            issue.BUG_ID: self.arbitrary_record['id']
        }
        actual_output = issue.to_taskwarrior()

        self.assertEqual(actual_output, expected_output)

    def test_issues(self):
        issue = next(self.service.issues())

        expected = {
            'annotations': [],
            'bugzillabugid': 1234567,
            'bugzillastatus': 'NEW',
            'bugzillasummary': 'This is the issue summary',
            'bugzillaurl': u'https://http://one.com//show_bug.cgi?id=1234567',
            'description': u'(bw)Is#1234567 - This is the issue summary .. https://http://one.com//show_bug.cgi?id=1234567',
            'priority': 'H',
            'project': 'Something',
            'tags': []}

        self.assertEqual(issue.get_taskwarrior_record(), expected)
