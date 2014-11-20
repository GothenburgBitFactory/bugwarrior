import mock

from bugwarrior.services.redmine import RedMineService

from .base import ServiceTest


class TestRedmineIssue(ServiceTest):
    SERVICE_CONFIG = {
        'redmine.url': 'something',
        'redmine.key': 'something_else',
        'redmine.user_id': '10834u0234',
    }

    def setUp(self):
        self.service = self.get_mock_service(RedMineService)

    def test_to_taskwarrior(self):
        arbitrary_url = 'http://lkjlj.com'
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

        issue = self.service.get_issue_for_record(arbitrary_issue)

        expected_output = {
            'project': arbitrary_issue['project']['name'],
            'priority': self.service.default_priority,

            issue.URL: arbitrary_url,
            issue.SUBJECT: arbitrary_issue['subject'],
            issue.ID: arbitrary_issue['id'],
        }

        def get_url(*args):
            return arbitrary_url

        with mock.patch.object(issue, 'get_issue_url', side_effect=get_url):
            actual_output = issue.to_taskwarrior()

        self.assertEqual(actual_output, expected_output)
