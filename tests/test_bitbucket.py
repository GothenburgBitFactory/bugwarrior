import responses

from bugwarrior.services.bitbucket import BitbucketService

from .base import ServiceTest, AbstractServiceTest


class TestBitbucketIssue(AbstractServiceTest, ServiceTest):
    SERVICE_CONFIG = {
        'service': 'bitbucket',
        'bitbucket.username': 'somename',
        'bitbucket.key': 'something',
        'bitbucket.secret': 'something else',
    }

    @responses.activate
    def setUp(self):
        super().setUp()

        self.add_response(
            'https://bitbucket.org/site/oauth2/access_token',
            method='POST',
            json={
                'access_token': 'sometoken',
                'refresh_token': 'anothertoken'
            }
        )
        self.service = self.get_mock_service(BitbucketService)

    def test_to_taskwarrior(self):
        arbitrary_issue = {
            'priority': 'trivial',
            'id': '100',
            'title': 'Some Title',
        }
        arbitrary_extra = {
            'url': 'http://hello-there.com/',
            'project': 'Something',
            'annotations': [
                'One',
            ]
        }

        issue = self.service.get_issue_for_record(
            arbitrary_issue, arbitrary_extra
        )

        expected_output = {
            'project': arbitrary_extra['project'],
            'priority': issue.PRIORITY_MAP[arbitrary_issue['priority']],
            'annotations': arbitrary_extra['annotations'],

            issue.URL: arbitrary_extra['url'],
            issue.FOREIGN_ID: arbitrary_issue['id'],
            issue.TITLE: arbitrary_issue['title'],
        }
        actual_output = issue.to_taskwarrior()

        self.assertEqual(actual_output, expected_output)

    @responses.activate
    def test_issues(self):
        self.add_response(
            'https://api.bitbucket.org/2.0/repositories/somename/',
            json={'values': [{
                'full_name': 'somename/somerepo',
                'has_issues': True
            }]})

        self.add_response(
            'https://api.bitbucket.org/2.0/repositories/somename/somerepo/issues/',
            json={'values': [{
                'title': 'Some Bug',
                'status': 'open',
                'links': {'html': {'href': 'example.com'}},
                'id': 1
            }]})

        self.add_response(
            'https://api.bitbucket.org/2.0/repositories/somename/somerepo/pullrequests/',
            json={'values': [{
                'title': 'Some Feature',
                'state': 'open',
                'links': {'html': {'href': 'example.com'}},
                'id': 1
            }]})

        self.add_response(
            'https://api.bitbucket.org/2.0/repositories/somename/somerepo/pullrequests/1/comments',
            json={'values': [{
                'user': {'username': 'nobody'},
                'content': {'raw': 'Some comment.'}
            }]})

        issue, pr = (i for i in self.service.issues())

        expected_issue = {
            'annotations': ['@nobody - Some comment.'],
            'bitbucketid': 1,
            'bitbuckettitle': 'Some Bug',
            'bitbucketurl': 'example.com',
            'description': '(bw)Is#1 - Some Bug .. example.com',
            'priority': 'M',
            'project': 'somerepo',
            'tags': []}

        self.assertEqual(issue.get_taskwarrior_record(), expected_issue)

        expected_pr = {
            'annotations': ['@nobody - Some comment.'],
            'bitbucketid': 1,
            'bitbuckettitle': 'Some Feature',
            'bitbucketurl': 'https://bitbucket.org/',
            'description': '(bw)Is#1 - Some Feature .. https://bitbucket.org/',
            'priority': 'M',
            'project': 'somerepo',
            'tags': []}

        self.assertEqual(pr.get_taskwarrior_record(), expected_pr)

    def test_get_owner(self):
        issue = {
            'title': 'Foobar',
            'assignee': {'username': 'tintin'},
        }
        self.assertEqual(self.service.get_owner(('foo', issue)), 'tintin')

    def test_get_owner_none(self):
        issue = {
            'title': 'Foobar',
            'assignee': None,
        }
        self.assertIsNone(self.service.get_owner(('foo', issue)))

    @responses.activate
    def test_fetch_issues_pagination(self):
        self.add_response(
            'https://api.bitbucket.org/2.0/repositories/somename/somerepo/issues/',
            json={
                'values': [{
                    'title': 'Some Bug',
                    'status': 'open',
                    'links': {'html': {'href': 'example.com'}},
                    'id': 1
                }],
                'next': 'https://api.bitbucket.org/2.0/repositories/somename/somerepo/issues/?page=2',  # noqa: E501
            })
        self.add_response(
            'https://api.bitbucket.org/2.0/repositories/somename/somerepo/issues/?page=2',
            json={
                'values': [{
                    'title': 'Some Other Bug',
                    'status': 'open',
                    'links': {'html': {'href': 'example.com'}},
                    'id': 2
                }],
            })
        issues = list(self.service.fetch_issues('somename/somerepo'))
        expected = [
            ('somename/somerepo', {
                'title': 'Some Bug',
                'status': 'open',
                'links': {'html': {'href': 'example.com'}},
                'id': 1
            }),
            ('somename/somerepo', {
                'title': 'Some Other Bug',
                'status': 'open',
                'links': {'html': {'href': 'example.com'}},
                'id': 2
            }),
        ]
        self.assertEqual(issues, expected)
