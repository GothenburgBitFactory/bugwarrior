from builtins import next
from builtins import object

import mock
from collections import namedtuple
from dateutil.tz import datetime
from dateutil.tz.tz import tzutc

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
            'fixVersions': [{'name': '1.2.3'}],
            'issuetype': {'name': 'Epic'},
            'status': {'name': 'Open'}
        },
        'key': '%s-%s' % (arbitrary_project, arbitrary_id, ),
    }

    arbitrary_record_with_due = arbitrary_record.copy()
    arbitrary_record_with_due['fields']=arbitrary_record_with_due['fields'].copy()
    arbitrary_record_with_due['fields']['Sprint']=['com.atlassian.greenhopper.service.sprint.Sprint@4c9c41a5[id=2322,rapidViewId=1173,\
                    state=ACTIVE,name=Sprint 1,startDate=2016-09-06T16:08:07.4\
                    55Z,endDate=2016-09-23T16:08:00.000Z,completeDate=<null>,sequence=2322]']

    def setUp(self):
        super(TestJiraIssue, self).setUp()
        with mock.patch('jira.client.JIRA._get_json'):
            self.service = self.get_mock_service(JiraService)

    def get_mock_service(self, *args, **kwargs):
        service = super(TestJiraIssue, self).get_mock_service(*args, **kwargs)
        service.jira = FakeJiraClient(self.arbitrary_record)
        service.sprint_field_names = ['Sprint']
        service.import_sprints_as_tags = True
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
            'due': None,
            'tags': [],
            'entry': datetime.datetime(2016, 6, 6, 13, 7, 8, tzinfo=tzutc()),
            'jirafixversion': '1.2.3',
            'jiraissuetype': 'Epic',
            'jirastatus': 'Open',

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

    def test_to_taskwarrior_sprint_with_goal(self):
        record_with_goal = self.arbitrary_record.copy()
        record_with_goal['fields'] = self.arbitrary_record_with_due['fields'].copy()
        record_with_goal['fields']['Sprint'] = [
            'com.atlassian.greenhopper.service.sprint.Sprint@4c9c41a5[id=2322,rapidViewId=1173,\
            state=ACTIVE,name=Sprint 1,goal=Do foo, bar, baz,startDate=2016-09-06T16:08:07.4\
            55Z,endDate=2016-09-23T16:08:00.000Z,completeDate=<null>,sequence=2322]'
        ]
        arbitrary_url = 'http://one'
        arbitrary_extra = {
            'jira_version': 5,
            'annotations': ['an annotation'],
        }

        issue = self.service.get_issue_for_record(
            record_with_goal, arbitrary_extra
        )

        expected_output = {
            'project': self.arbitrary_project,
            'priority': (
                issue.PRIORITY_MAP[record_with_goal['fields']['priority']]
            ),
            'annotations': arbitrary_extra['annotations'],
            'due': datetime.datetime(2016, 9, 23, 16, 8, tzinfo=tzutc()),
            'tags': ['Sprint1'],
            'entry': datetime.datetime(2016, 6, 6, 13, 7, 8, tzinfo=tzutc()),
            'jirafixversion': '1.2.3',
            'jiraissuetype': 'Epic',
            'jirastatus': 'Open',

            issue.URL: arbitrary_url,
            issue.FOREIGN_ID: record_with_goal['key'],
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
            'due': None,
            'description': '(bw)Is#10 - lkjaldsfjaldf .. two/browse/DONUT-10',
            'entry': datetime.datetime(2016, 6, 6, 13, 7, 8, tzinfo=tzutc()),
            'jiradescription': None,
            'jiraestimate': 1,
            'jirafixversion': '1.2.3',
            'jiraid': 'DONUT-10',
            'jiraissuetype': 'Epic',
            'jirastatus': 'Open',
            'jirasummary': 'lkjaldsfjaldf',
            'jiraurl': 'two/browse/DONUT-10',
            'priority': 'H',
            'project': 'DONUT',
            'tags': []}

        self.assertEqual(issue.get_taskwarrior_record(), expected)

    def test_get_due(self):
        issue = self.service.get_issue_for_record(
            self.arbitrary_record_with_due
        )
        self.assertEqual(issue.get_due(), datetime.datetime(2016, 9, 23, 16, 8, tzinfo=tzutc()))
