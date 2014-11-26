import datetime

import pytz

from bugwarrior.services.github import GithubService

from .base import ServiceTest


class TestGithubIssue(ServiceTest):
    SERVICE_CONFIG = {
        'github.login': 'arbitrary_login',
        'github.password': 'arbitrary_password',
        'github.username': 'arbitrary_username',
    }

    def setUp(self):
        self.service = self.get_mock_service(GithubService)

    def test_to_taskwarrior(self):
        arbitrary_created = (
            datetime.datetime.utcnow() - datetime.timedelta(hours=1)
        ).replace(tzinfo=pytz.UTC)
        arbitrary_updated = datetime.datetime.utcnow().replace(tzinfo=pytz.UTC)
        arbitrary_issue = {
            'title': 'Hallo',
            'html_url': 'http://whanot.com/',
            'number': 10,
            'body': 'Something',
            'milestone': {'id': 'alpha'},
            'labels': [
                {'name': 'bugfix'},
            ],
            'created_at': arbitrary_created.isoformat(),
            'updated_at': arbitrary_updated.isoformat(),
        }
        arbitrary_extra = {
            'project': 'one',
            'type': 'issue',
            'annotations': [],
        }

        self.service.import_labels_as_tags = True
        issue = self.service.get_issue_for_record(
            arbitrary_issue,
            arbitrary_extra
        )

        expected_output = {
            'project': arbitrary_extra['project'],
            'priority': self.service.default_priority,
            'annotations': [],
            'tags': ['bugfix'],

            issue.URL: arbitrary_issue['html_url'],
            issue.TYPE: arbitrary_extra['type'],
            issue.TITLE: arbitrary_issue['title'],
            issue.NUMBER: arbitrary_issue['number'],
            issue.UPDATED_AT: arbitrary_updated,
            issue.CREATED_AT: arbitrary_created,
            issue.BODY: arbitrary_issue['body'],
            issue.MILESTONE: arbitrary_issue['milestone']['id'],
        }
        actual_output = issue.to_taskwarrior()

        self.assertEqual(actual_output, expected_output)
