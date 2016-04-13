from bugwarrior.services.taiga import TaigaService

from .base import ServiceTest


class TestTaigaIssue(ServiceTest):
    SERVICE_CONFIG = {
        'taiga.base_uri': 'one',
        'taiga.auth_token': 'two',
    }

    def setUp(self):
        self.service = self.get_mock_service(TaigaService)

    def test_to_taskwarrior(self):
        record = {
            'ref': 40,
            'subject': 'this is a title',
            'tags': [
                'bugwarrior',
            ],
        }
        extra = {
            'project': 'awesome',
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
            'project': 'awesome',
            'tags': ['bugwarrior'],
            'taigaid': 40,
            'taigasummary': 'this is a title',
            'taigaurl': 'this is a url',
        }

        self.assertEqual(actual, expected)
