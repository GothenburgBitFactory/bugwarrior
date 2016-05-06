import mock
import responses

from bugwarrior.services.redmine import RedMineService

from .base import ServiceTest, AbstractServiceTest


class TestRedmineIssue(AbstractServiceTest, ServiceTest):
    SERVICE_CONFIG = {
        'redmine.url': 'https://something',
        'redmine.key': 'something_else',
        'redmine.user_id': '10834u0234',
    }
    arbitrary_issue = {
        "assigned_to": {
            "id": 35546,
            "name": "Adam Coddington"
        },
        "author": {
            "id": 35546,
            "name": "Adam Coddington"
        },
        "created_on": "2014-11-19T16:40:29Z",
        "description": "This is a test issue.",
        "done_ratio": 0,
        "id": 363901,
        "priority": {
            "id": 4,
            "name": "Normal"
        },
        "project": {
            "id": 27375,
            "name": "Bugwarrior"
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
        "updated_on": "2014-11-19T16:40:29Z"
    }

    def setUp(self):
        self.service = self.get_mock_service(RedMineService)

    def test_to_taskwarrior(self):
        arbitrary_url = 'http://lkjlj.com'

        issue = self.service.get_issue_for_record(self.arbitrary_issue)

        expected_output = {
            'project': self.arbitrary_issue['project']['name'],
            'priority': self.service.default_priority,

            issue.URL: arbitrary_url,
            issue.SUBJECT: self.arbitrary_issue['subject'],
            issue.ID: self.arbitrary_issue['id'],
        }

        def get_url(*args):
            return arbitrary_url

        with mock.patch.object(issue, 'get_issue_url', side_effect=get_url):
            actual_output = issue.to_taskwarrior()

        self.assertEqual(actual_output, expected_output)

    @responses.activate
    def test_issues(self):
        self.add_response(
            'https://something/issues.json?assigned_to_id=10834u0234',
            json={'issues': [self.arbitrary_issue]})

        issue = next(self.service.issues())

        expected = {
            'description':
                u'(bw)Is#363901 - Biscuits .. https://something/issues/363901',
            'priority': 'M',
            'project': u'Bugwarrior',
            'redmineid': 363901,
            'redminesubject': u'Biscuits',
            'redmineurl': u'https://something/issues/363901',
            'tags': []}

        self.assertEqual(issue.get_taskwarrior_record(), expected)
