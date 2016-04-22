from bugwarrior.services.gerrit import GerritService

from .base import ServiceTest


class TestGerritIssue(ServiceTest):
    SERVICE_CONFIG = {
        'gerrit.base_uri': 'one',
        'gerrit.username': 'two',
        'gerrit.password': 'three',
    }

    def setUp(self):
        self.service = self.get_mock_service(GerritService)

    def test_to_taskwarrior(self):
        record = {
            'project': 'nova',
            '_number': 1,
            'subject': 'this is a title',
        }
        extra = {
            'annotations': [
                # TODO - test annotations?
            ],
            'url': 'this is a url',
        }

        issue = self.service.get_issue_for_record(record, extra)
        actual = issue.to_taskwarrior()
        expected = {
            'annotations': [],
            'priority': 'M',
            'project': 'nova',
            'gerritid': 1,
            'gerritsummary': 'this is a title',
            'gerriturl': 'this is a url',
            'tags': [],
        }

        self.assertEqual(actual, expected)
