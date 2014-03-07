import mock

from bugwarrior.services.teamlab import TeamLabService

from .base import ServiceTest


class TestTeamlabIssue(ServiceTest):
    SERVICE_CONFIG = {
        'teamlab.hostname': 'something',
        'teamlab.login': 'alkjdsf',
        'teamlab.password': 'lkjklj',
        'teamlab.project_name': 'abcdef',
    }

    def setUp(self):
        with mock.patch(
            'bugwarrior.services.teamlab.TeamLabClient.authenticate'
        ):
            self.service = self.get_mock_service(TeamLabService)

    def test_to_taskwarrior(self):
        arbitrary_url = 'http://galkjsdflkj.com/'
        arbitrary_issue = {
            'title': 'Hello',
            'id': 10,
            'projectOwner': {
                'id': 140,
            }
        }

        issue = self.service.get_issue_for_record(arbitrary_issue)

        expected_output = {
            'project': self.SERVICE_CONFIG['teamlab.project_name'],
            'priority': self.service.default_priority,
            issue.TITLE: arbitrary_issue['title'],
            issue.FOREIGN_ID: arbitrary_issue['id'],
            issue.URL: arbitrary_url,
            issue.PROJECTOWNER_ID: arbitrary_issue['projectOwner']['id']
        }

        def get_url(*args):
            return arbitrary_url

        with mock.patch.object(issue, 'get_issue_url', side_effect=get_url):
            actual_output = issue.to_taskwarrior()

        self.assertEqual(actual_output, expected_output)
