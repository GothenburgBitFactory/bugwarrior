from builtins import next
import datetime

import mock
import dateutil
import responses

from bugwarrior.services.redmine import RedMineService

from .base import ServiceTest, AbstractServiceTest


class TestRedmineIssue(AbstractServiceTest, ServiceTest):
    maxDiff = None
    SERVICE_CONFIG = {
        'redmine.url': 'https://something',
        'redmine.key': 'something_else',
        'redmine.issue_limit': '100',
    }
    arbitrary_created = datetime.datetime.utcnow().replace(
        tzinfo=dateutil.tz.tz.tzutc(), microsecond=0) - datetime.timedelta(1)
    arbitrary_updated = datetime.datetime.utcnow().replace(
        tzinfo=dateutil.tz.tz.tzutc(), microsecond=0)
    arbitrary_issue = {
        "assigned_to": {
            "id": 35546,
            "name": "Adam Coddington"
        },
        "author": {
            "id": 35546,
            "name": "Adam Coddington"
        },
        "created_on": arbitrary_created.isoformat(),
        "due_on": "2016-12-30T16:40:29Z",
        "description": "This is a test issue.",
        "done_ratio": 0,
        "id": 363901,
        "priority": {
            "id": 4,
            "name": "Normal"
        },
        "project": {
            "id": 27375,
            "name": "Boiled Cabbage - Yum"
        },
        "status": {
            "id": 1,
            "name": "New"
        },
        "subject": "Biscuits",
        "tracker": {
            "id": 4,
            "name": "Task"
        },
        "updated_on": arbitrary_updated.isoformat(),
    }

    def setUp(self):
        super(TestRedmineIssue, self).setUp()
        self.service = self.get_mock_service(RedMineService)

    def test_to_taskwarrior(self):
        arbitrary_url = 'http://lkjlj.com'

        issue = self.service.get_issue_for_record(self.arbitrary_issue)

        expected_output = {
            'annotations': [],
            'project': issue.get_project_name(),
            'priority': self.service.default_priority,
            issue.DUEDATE: None,
            issue.ASSIGNED_TO: self.arbitrary_issue['assigned_to']['name'],
            issue.AUTHOR: self.arbitrary_issue['author']['name'],
            issue.CATEGORY: None,
            issue.DESCRIPTION: self.arbitrary_issue['description'],
            issue.ESTIMATED_HOURS: None,
            issue.STATUS: 'New',
            issue.URL: arbitrary_url,
            issue.SUBJECT: self.arbitrary_issue['subject'],
            issue.TRACKER: u'Task',
            issue.CREATED_ON: self.arbitrary_created,
            issue.UPDATED_ON: self.arbitrary_updated,
            issue.ID: self.arbitrary_issue['id'],
            issue.SPENT_HOURS: None,
            issue.START_DATE: None,
        }

        def get_url(*args):
            return arbitrary_url

        with mock.patch.object(issue, 'get_issue_url', side_effect=get_url):
            actual_output = issue.to_taskwarrior()

        self.assertEqual(actual_output, expected_output)

    @responses.activate
    def test_issues(self):
        self.add_response(
            'https://something/issues.json?limit=100',
            json={'issues': [self.arbitrary_issue]})

        issue = next(self.service.issues())

        expected = {
            'annotations': [],
            issue.DUEDATE: None,
            'description':
                u'(bw)Is#363901 - Biscuits .. https://something/issues/363901',
            'priority': 'M',
            'project': u'boiledcabbageyum',
            'redmineid': 363901,
            issue.SPENT_HOURS: None,
            issue.START_DATE: None,
            'redmineassignedto': 'Adam Coddington',
            'redmineauthor': 'Adam Coddington',
            issue.CATEGORY: None,
            issue.DESCRIPTION: self.arbitrary_issue['description'],
            issue.ESTIMATED_HOURS: None,
            issue.STATUS: 'New',
            'redminesubject': u'Biscuits',
            'redminetracker': u'Task',
            issue.CREATED_ON: self.arbitrary_created,
            issue.UPDATED_ON: self.arbitrary_updated,
            'redmineurl': u'https://something/issues/363901',
            'tags': []}

        self.assertEqual(issue.get_taskwarrior_record(), expected)
