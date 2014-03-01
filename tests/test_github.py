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
        arbitrary_issue = {
            'title': 'Hallo',
            'html_url': 'http://whanot.com/',
            'number': 10
        }
        arbitrary_extra = {
            'project': 'one',
            'type': 'issue',
            'annotations': [],
        }

        issue = self.service.get_issue_for_record(
            arbitrary_issue,
            arbitrary_extra
        )

        expected_output = {
            'project': arbitrary_extra['project'],
            'priority': self.service.default_priority,
            'annotations': [],

            issue.URL: arbitrary_issue['html_url'],
            issue.TYPE: arbitrary_extra['type'],
            issue.TITLE: arbitrary_issue['title'],
            issue.NUMBER: arbitrary_issue['number'],
        }
        actual_output = issue.to_taskwarrior()

        self.assertEqual(actual_output, expected_output)
