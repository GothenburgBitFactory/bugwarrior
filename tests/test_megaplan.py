import mock

from bugwarrior.services.mplan import MegaplanService

from .base import ServiceTest


class TestMegaplanIssue(ServiceTest):
    SERVICE_CONFIG = {
        'megaplan.hostname': 'something',
        'megaplan.login': 'something_else',
        'megaplan.password': 'aljlkj',
    }

    def setUp(self):
        with mock.patch('megaplan.Client'):
            self.service = self.get_mock_service(MegaplanService)

    def test_to_taskwarrior(self):
        arbitrary_project = 'one'
        arbitrary_url = 'http://one.com/'
        name_parts = ['one', 'two', 'three']
        arbitrary_issue = {
            'Id': 10,
            'Name': '|'.join(name_parts)
        }

        issue = self.service.get_issue_for_record(arbitrary_issue)

        expected_output = {
            'project': arbitrary_project,
            'priority': self.service.default_priority,

            issue.FOREIGN_ID: arbitrary_issue['Id'],
            issue.URL: arbitrary_url,
            issue.TITLE: name_parts[-1]
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
