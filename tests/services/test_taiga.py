import pytest
import responses

from bugwarrior.collect import TaskConstructor
from bugwarrior.services.taiga import TaigaService

from .base import get_mock_service

SERVICE_CONFIG = {'service': 'taiga', 'base_uri': 'https://one', 'auth_token': 'two'}


@pytest.fixture
def record():
    return {
        'id': 400,
        'project': 4,
        'ref': 40,
        'subject': 'this is a title',
        'tags': ['single', ['bugwarrior', None], ['task', '#c0ffee']],
        'due_date': '2026-05-18',
    }


class TestTaigaIssue:
    @pytest.fixture
    def service(self):
        return get_mock_service(TaigaService, SERVICE_CONFIG)

    def test_to_taskwarrior(self, service, record):
        extra = {
            'project': 'awesome',
            'annotations': [
                # TODO - test annotations?
            ],
            'url': 'this is a url',
        }

        issue = service.get_issue_for_record(record, extra)
        actual = issue.to_taskwarrior()
        expected = {
            'annotations': [],
            'priority': 'M',
            'project': 'awesome',
            'tags': ['single', 'bugwarrior', 'task'],
            'taigaid': 40,
            'taigasummary': 'this is a title',
            'taigaurl': 'this is a url',
            'due': issue.parse_date('2026-05-18'),
        }

        assert actual == expected

    @responses.activate
    def test_issues(self, service, record):
        userid = 1

        responses.get('https://one/api/v1/users/me', json={'id': userid})

        responses.get(
            'https://one/api/v1/userstories?status__is_closed=false&assigned_to={}'.format(
                userid
            ),
            json=[record],
        )

        responses.get(
            'https://one/api/v1/projects/{}'.format(record['project']),
            json={'slug': 'something'},
        )

        responses.get(
            'https://one/api/v1/history/userstory/{}'.format(record['id']),
            json=[{'user': {'username': 'you'}, 'comment': 'Blah blah blah!'}],
        )

        issue = next(service.issues())

        expected = {
            'annotations': ['@you - Blah blah blah!'],
            'description': '(bw)Is#40 - this is a title .. https://one/project/something/us/40',
            'priority': 'M',
            'project': 'something',
            'tags': ['single', 'bugwarrior', 'task'],
            'taigaid': 40,
            'taigasummary': 'this is a title',
            'taigaurl': 'https://one/project/something/us/40',
            'due': issue.parse_date('2026-05-18'),
        }

        assert TaskConstructor(issue).get_taskwarrior_record() == expected
