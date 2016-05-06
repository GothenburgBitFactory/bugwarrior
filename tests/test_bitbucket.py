import responses

from bugwarrior.services.bitbucket import BitbucketService

from .base import ServiceTest


class TestBitbucketIssue(ServiceTest):
    SERVICE_CONFIG = {
        'bitbucket.login': 'something',
        'bitbucket.username': 'somename',
        'bitbucket.password': 'something else',
    }

    def setUp(self):
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
        responses.add(
            responses.GET,
            'https://api.bitbucket.org/2.0/repositories/somename/',
            json={'values': [{
                'full_name': 'somename/somerepo',
                'has_issues': True
            }]})

        responses.add(
            responses.GET,
            'https://api.bitbucket.org/2.0/repositories/somename/somerepo/issues/',
            json={'values': [{
                'title': 'Some Bug',
                'status': 'open',
                'links': {'html': {'href': 'example.com'}},
                'id': 1
            }]})

        responses.add(
            responses.GET,
            'https://api.bitbucket.org/1.0/repositories/somename/somerepo/issues/1/comments',
            json=[{
                'author_info': {'username': 'nobody'},
                'content': 'Some comment.'
            }])

        responses.add(
            responses.GET,
            'https://api.bitbucket.org/2.0/repositories/somename/somerepo/pullrequests/',
            json={'values': [{
                'title': 'Some Feature',
                'state': 'open',
                'links': {'html': {'href': 'example.com'}},
                'id': 1
            }]})

        responses.add(
            responses.GET,
            'https://api.bitbucket.org/2.0/repositories/somename/somerepo/pullrequests/1/comments',
            json={'values': [{
                'user': {'username': 'nobody'},
                'content': {'raw': 'Some comment.'}
            }]})

        issue, pr = [i for i in self.service.issues()]

        expected_issue = {
            'annotations': [u'@nobody - Some comment.'],
            'bitbucketid': 1,
            'bitbuckettitle': u'Some Bug',
            'bitbucketurl': u'example.com',
            'description': u'(bw)Is#1 - Some Bug .. example.com',
            'priority': 'M',
            'project': u'somerepo',
            'tags': []}

        self.assertEqual(issue.get_taskwarrior_record(), expected_issue)

        expected_pr = {
            'annotations': [u'@nobody - Some comment.'],
            'bitbucketid': 1,
            'bitbuckettitle': u'Some Feature',
            'bitbucketurl': 'https://bitbucket.org/',
            'description': u'(bw)Is#1 - Some Feature .. https://bitbucket.org/',
            'priority': 'M',
            'project': u'somerepo',
            'tags': []}

        self.assertEqual(pr.get_taskwarrior_record(), expected_pr)
