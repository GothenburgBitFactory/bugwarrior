import pytest
import responses

from bugwarrior.collect import TaskConstructor
from bugwarrior.services.bitbucket import BitbucketService

from .base import get_mock_service

SERVICE_CONFIG = {
    'service': 'bitbucket',
    'username': 'somename',
    'key': 'something',
    'secret': 'something else',
}


@pytest.fixture
def record():
    return {'priority': 'trivial', 'id': '100', 'title': 'Some Title'}


@pytest.fixture
def extra():
    return {
        'url': 'http://hello-there.com/',
        'project': 'Something',
        'annotations': ['One'],
    }


class TestBitbucketIssue:
    @pytest.fixture
    def service(self):
        with responses.mock:
            responses.post(
                'https://bitbucket.org/site/oauth2/access_token',
                json={'access_token': 'sometoken', 'refresh_token': 'anothertoken'},
            )
            return get_mock_service(BitbucketService, SERVICE_CONFIG)

    def test_to_taskwarrior(self, service, record, extra):
        issue = service.get_issue_for_record(record, extra)

        expected_output = {
            'project': extra['project'],
            'priority': issue.PRIORITY_MAP[record['priority']],
            'annotations': extra['annotations'],
            issue.URL: extra['url'],
            issue.FOREIGN_ID: record['id'],
            issue.TITLE: record['title'],
        }
        actual_output = issue.to_taskwarrior()

        assert actual_output == expected_output

    @responses.activate
    def test_issues(self, service):
        responses.get(
            'https://api.bitbucket.org/2.0/repositories/somename/',
            json={'values': [{'full_name': 'somename/somerepo', 'has_issues': True}]},
        )

        responses.get(
            'https://api.bitbucket.org/2.0/repositories/somename/somerepo/issues/',
            json={
                'values': [
                    {
                        'title': 'Some Bug',
                        'status': 'open',
                        'links': {'html': {'href': 'example.com'}},
                        'id': 1,
                    }
                ]
            },
        )

        responses.get(
            'https://api.bitbucket.org/2.0/repositories/somename/somerepo/pullrequests/',
            json={
                'values': [
                    {
                        'title': 'Some Feature',
                        'state': 'open',
                        'links': {'html': {'href': 'example.com'}},
                        'id': 1,
                    }
                ]
            },
        )

        responses.get(
            'https://api.bitbucket.org/2.0/repositories/somename/somerepo/pullrequests/1/comments',
            json={
                'values': [
                    {
                        'user': {'username': 'nobody'},
                        'content': {'raw': 'Some comment.'},
                    }
                ]
            },
        )

        issue, pr = (i for i in service.issues())

        expected_issue = {
            'annotations': ['@nobody - Some comment.'],
            'bitbucketid': 1,
            'bitbuckettitle': 'Some Bug',
            'bitbucketurl': 'example.com',
            'description': '(bw)Is#1 - Some Bug .. example.com',
            'priority': 'M',
            'project': 'somerepo',
            'tags': [],
        }

        assert TaskConstructor(issue).get_taskwarrior_record() == expected_issue

        expected_pr = {
            'annotations': ['@nobody - Some comment.'],
            'bitbucketid': 1,
            'bitbuckettitle': 'Some Feature',
            'bitbucketurl': 'https://bitbucket.org/',
            'description': '(bw)Is#1 - Some Feature .. https://bitbucket.org/',
            'priority': 'M',
            'project': 'somerepo',
            'tags': [],
        }

        assert TaskConstructor(pr).get_taskwarrior_record() == expected_pr

    def test_get_owner(self, service):
        issue = {'title': 'Foobar', 'assignee': {'username': 'tintin'}}
        assert service.get_owner(('foo', issue)) == 'tintin'

    def test_get_owner_none(self, service):
        issue = {'title': 'Foobar', 'assignee': None}
        assert service.get_owner(('foo', issue)) is None

    @responses.activate
    def test_fetch_issues_pagination(self, service):
        responses.get(
            'https://api.bitbucket.org/2.0/repositories/somename/somerepo/issues/',
            json={
                'values': [
                    {
                        'title': 'Some Bug',
                        'status': 'open',
                        'links': {'html': {'href': 'example.com'}},
                        'id': 1,
                    }
                ],
                'next': 'https://api.bitbucket.org/2.0/repositories/somename/somerepo/issues/?page=2',  # noqa: E501
            },
        )
        responses.get(
            'https://api.bitbucket.org/2.0/repositories/somename/somerepo/issues/?page=2',
            json={
                'values': [
                    {
                        'title': 'Some Other Bug',
                        'status': 'open',
                        'links': {'html': {'href': 'example.com'}},
                        'id': 2,
                    }
                ]
            },
        )
        issues = list(service.fetch_issues('somename/somerepo'))
        expected = [
            (
                'somename/somerepo',
                {
                    'title': 'Some Bug',
                    'status': 'open',
                    'links': {'html': {'href': 'example.com'}},
                    'id': 1,
                },
            ),
            (
                'somename/somerepo',
                {
                    'title': 'Some Other Bug',
                    'status': 'open',
                    'links': {'html': {'href': 'example.com'}},
                    'id': 2,
                },
            ),
        ]
        assert issues == expected
