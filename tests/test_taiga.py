import responses

from bugwarrior.services.taiga import TaigaService

from .base import ServiceTest, AbstractServiceTest


class TestTaigaIssue(AbstractServiceTest, ServiceTest):
    SERVICE_CONFIG = {
        'service': 'taiga',
        'taiga.base_uri': 'https://one',
        'taiga.auth_token': 'two',
    }
    record = {
        'id': 400,
        'project': 4,
        'ref': 40,
        'subject': 'this is a title',
        'tags': [
            'single',
            [
                'bugwarrior',
                None
            ],
            [
                'task',
                '#c0ffee'
            ]
        ],
    }

    def setUp(self):
        super().setUp()
        self.service = self.get_mock_service(TaigaService)

    def test_to_taskwarrior(self):
        extra = {
            'project': 'awesome',
            'annotations': [
                # TODO - test annotations?
            ],
            'url': 'this is a url',
        }

        issue = self.service.get_issue_for_record(self.record, extra)
        actual = issue.to_taskwarrior()
        expected = {
            'annotations': [],
            'priority': 'M',
            'project': 'awesome',
            'tags': ['single', 'bugwarrior', 'task'],
            'taigaid': 40,
            'taigasummary': 'this is a title',
            'taigaurl': 'this is a url',
        }

        self.assertEqual(actual, expected)

    @responses.activate
    def test_issues(self):
        userid = 1

        self.add_response(
            'https://one/api/v1/users/me',
            json={'id': userid})

        self.add_response(
            'https://one/api/v1/userstories?status__is_closed=false&assigned_to={}'.format(
                userid),
            json=[self.record])

        self.add_response(
            'https://one/api/v1/projects/{}'.format(self.record['project']),
            json={'slug': 'something'})

        self.add_response(
            'https://one/api/v1/history/userstory/{}'.format(
                self.record['id']),
            json=[{'user': {'username': 'you'}, 'comment': 'Blah blah blah!'}])

        issue = next(self.service.issues())

        expected = {
            'annotations': ['@you - Blah blah blah!'],
            'description':
                '(bw)Is#40 - this is a title .. https://one/project/something/us/40',
            'priority': 'M',
            'project': 'something',
            'tags': ['single', 'bugwarrior', 'task'],
            'taigaid': 40,
            'taigasummary': 'this is a title',
            'taigaurl': 'https://one/project/something/us/40'}

        self.assertEqual(issue.get_taskwarrior_record(), expected)
