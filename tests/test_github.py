import datetime
from unittest import TestCase

import pytz
import responses

from bugwarrior.services.github import (
    GithubConfig, GithubService, GithubClient)

from .base import ServiceTest, AbstractServiceTest


ARBITRARY_CREATED = (
    datetime.datetime.utcnow() - datetime.timedelta(hours=1)
).replace(tzinfo=pytz.UTC, microsecond=0)
ARBITRARY_CLOSED = (
    datetime.datetime.utcnow() - datetime.timedelta(minutes=30)
).replace(tzinfo=pytz.UTC, microsecond=0)
ARBITRARY_UPDATED = datetime.datetime.utcnow().replace(
    tzinfo=pytz.UTC, microsecond=0)
ARBITRARY_ISSUE = {
    'title': 'Hallo',
    'html_url': 'https://github.com/arbitrary_username/arbitrary_repo/pull/1',
    'url': 'https://api.github.com/repos/arbitrary_username/arbitrary_repo/issues/1',
    'number': 10,
    'body': 'Something',
    'user': {'login': 'arbitrary_login'},
    'milestone': {'title': 'alpha'},
    'labels': [{'name': 'bugfix'}],
    'created_at': ARBITRARY_CREATED.isoformat(),
    'closed_at': ARBITRARY_CLOSED.isoformat(),
    'updated_at': ARBITRARY_UPDATED.isoformat(),
    'repo': 'arbitrary_username/arbitrary_repo',
    'state': 'closed'
}
ARBITRARY_EXTRA = {
    'project': 'one',
    'type': 'issue',
    'annotations': [],
    'body': 'Something',
    'namespace': 'arbitrary_username',
}


class TestGithubIssue(AbstractServiceTest, ServiceTest):
    maxDiff = None
    SERVICE_CONFIG = {
        'service': 'github',
        'github.login': 'arbitrary_login',
        'github.token': 'arbitrary_token',
        'github.username': 'arbitrary_username',
    }

    def test_to_taskwarrior(self):
        service = self.get_mock_service(GithubService, config_overrides={
            'github.import_labels_as_tags': True})
        issue = service.get_issue_for_record(
            ARBITRARY_ISSUE,
            ARBITRARY_EXTRA
        )

        expected_output = {
            'project': ARBITRARY_EXTRA['project'],
            'priority': service.config.default_priority,
            'annotations': [],
            'tags': ['bugfix'],
            'entry': ARBITRARY_CREATED,
            'end': ARBITRARY_CLOSED,
            issue.URL: ARBITRARY_ISSUE['html_url'],
            issue.REPO: ARBITRARY_ISSUE['repo'],
            issue.TYPE: ARBITRARY_EXTRA['type'],
            issue.TITLE: ARBITRARY_ISSUE['title'],
            issue.NUMBER: ARBITRARY_ISSUE['number'],
            issue.UPDATED_AT: ARBITRARY_UPDATED,
            issue.CREATED_AT: ARBITRARY_CREATED,
            issue.CLOSED_AT: ARBITRARY_CLOSED,
            issue.BODY: ARBITRARY_EXTRA['body'],
            issue.MILESTONE: ARBITRARY_ISSUE['milestone']['title'],
            issue.USER: ARBITRARY_ISSUE['user']['login'],
            issue.NAMESPACE: 'arbitrary_username',
            issue.STATE: 'closed',
        }
        actual_output = issue.to_taskwarrior()

        self.assertEqual(actual_output, expected_output)

    @responses.activate
    def test_issues(self):
        self.add_response(
            'https://api.github.com/user/repos?per_page=100',
            json=[{
                'name': 'some_repo',
                'owner': {'login': 'some_username'}
            }])

        self.add_response(
            'https://api.github.com/users/arbitrary_username/repos?per_page=100',
            json=[{
                'name': 'arbitrary_repo',
                'owner': {'login': 'arbitrary_username'}
            }])

        self.add_response(
            'https://api.github.com/repos/arbitrary_username/arbitrary_repo/issues?per_page=100',
            json=[ARBITRARY_ISSUE])

        self.add_response(
            'https://api.github.com/issues?per_page=100',
            json=[ARBITRARY_ISSUE])

        self.add_response(
            'https://api.github.com/repos/arbitrary_username/arbitrary_repo/issues/10/comments?per_page=100',  # noqa: E501
            json=[{
                'user': {'login': 'arbitrary_login'},
                'body': 'Arbitrary comment.'
            }])

        service = self.get_mock_service(GithubService)
        issue = next(service.issues())

        expected = {
            'annotations': ['@arbitrary_login - Arbitrary comment.'],
            'description': '(bw)Is#10 - Hallo .. https://github.com/arbitrary_username/arbitrary_repo/pull/1',  # noqa: E501
            'entry': ARBITRARY_CREATED,
            'end': ARBITRARY_CLOSED,
            'githubbody': 'Something',
            'githubcreatedon': ARBITRARY_CREATED,
            'githubclosedon': ARBITRARY_CLOSED,
            'githubmilestone': 'alpha',
            'githubnamespace': 'arbitrary_username',
            'githubnumber': 10,
            'githubrepo': 'arbitrary_username/arbitrary_repo',
            'githubtitle': 'Hallo',
            'githubtype': 'issue',
            'githubupdatedat': ARBITRARY_UPDATED,
            'githuburl': 'https://github.com/arbitrary_username/arbitrary_repo/pull/1',
            'githubuser': 'arbitrary_login',
            'githubstate': 'closed',
            'priority': 'M',
            'project': 'arbitrary_repo',
            'tags': []}

        self.assertEqual(issue.get_taskwarrior_record(), expected)


class TestGithubIssueQuery(AbstractServiceTest, ServiceTest):
    maxDiff = None
    SERVICE_CONFIG = {
        'service': 'github',
        'github.login': 'arbitrary_login',
        'github.token': 'arbitrary_token',
        'github.username': 'arbitrary_username',
        'github.query': 'is:open reviewer:octocat',
        'github.include_user_repos': 'False',
        'github.include_user_issues': 'False',
    }

    def setUp(self):
        super().setUp()
        self.service = self.get_mock_service(GithubService)

    def test_to_taskwarrior(self):
        pass

    @responses.activate
    def test_issues(self):
        self.add_response(
            'https://api.github.com/search/issues?q=is%3Aopen+reviewer%3Aoctocat&per_page=100',
            json={'items': [ARBITRARY_ISSUE]})

        self.add_response(
            'https://api.github.com/repos/arbitrary_username/arbitrary_repo/issues/10/comments?per_page=100',  # noqa: E501
            json=[{
                'user': {'login': 'arbitrary_login'},
                'body': 'Arbitrary comment.'
            }])

        issue = list(self.service.issues())[0]

        expected = {
            'annotations': ['@arbitrary_login - Arbitrary comment.'],
            'description': '(bw)Is#10 - Hallo .. https://github.com/arbitrary_username/arbitrary_repo/pull/1',  # noqa: E501
            'entry': ARBITRARY_CREATED,
            'end': ARBITRARY_CLOSED,
            'githubbody': 'Something',
            'githubcreatedon': ARBITRARY_CREATED,
            'githubclosedon': ARBITRARY_CLOSED,
            'githubmilestone': 'alpha',
            'githubnamespace': 'arbitrary_username',
            'githubnumber': 10,
            'githubrepo': 'arbitrary_username/arbitrary_repo',
            'githubtitle': 'Hallo',
            'githubtype': 'issue',
            'githubupdatedat': ARBITRARY_UPDATED,
            'githuburl': 'https://github.com/arbitrary_username/arbitrary_repo/pull/1',
            'githubuser': 'arbitrary_login',
            'githubstate': 'closed',
            'priority': 'M',
            'project': 'arbitrary_repo',
            'tags': []}

        self.assertEqual(issue.get_taskwarrior_record(), expected)


class TestGithubService(ServiceTest):
    SERVICE_CONFIG = {
        'service': 'github',
        'github.login': 'tintin',
        'github.username': 'milou',
        'github.token': 't0ps3cr3t',

    }

    def test_token_authorization_header(self):
        service = self.get_mock_service(GithubService)
        service = self.get_mock_service(GithubService, config_overrides={
            'github.token': '@oracle:eval:echo 1234567890ABCDEF'})
        self.assertEqual(service.client.session.headers['Authorization'],
                         "token 1234567890ABCDEF")

    def test_default_host(self):
        """ Check that if github.host is not set, we default to github.com """
        service = self.get_mock_service(GithubService)
        self.assertEqual("github.com", service.config.host)

    def test_overwrite_host(self):
        """ Check that if github.host is set, we use its value as host """
        service = self.get_mock_service(GithubService, config_overrides={
            'github.host': 'github.example.com'})
        self.assertEqual("github.example.com", service.config.host)

    def test_keyring_service(self):
        """ Checks that the keyring service name """
        service_config = GithubConfig(**self.SERVICE_CONFIG)
        keyring_service = GithubService.get_keyring_service(service_config)
        self.assertEqual("github://tintin@github.com/milou", keyring_service)

    def test_keyring_service_host(self):
        """ Checks that the keyring key depends on the github host. """
        service_config = GithubConfig(**{'github.host': 'github.example.com'},
                                      **self.SERVICE_CONFIG)
        keyring_service = GithubService.get_keyring_service(service_config)
        self.assertEqual("github://tintin@github.example.com/milou", keyring_service)

    def test_get_repository_from_issue_url__issue(self):
        issue = dict(repos_url="https://github.com/foo/bar")
        repository = GithubService.get_repository_from_issue(issue)
        self.assertEqual("foo/bar", repository)

    def test_get_repository_from_issue_url__pull_request(self):
        issue = dict(repos_url="https://github.com/foo/bar")
        repository = GithubService.get_repository_from_issue(issue)
        self.assertEqual("foo/bar", repository)

    def test_get_repository_from_issue__enterprise_github(self):
        issue = dict(repos_url="https://github.acme.biz/foo/bar")
        repository = GithubService.get_repository_from_issue(issue)
        self.assertEqual("foo/bar", repository)

    def test_body_no_limit(self):
        service = self.get_mock_service(GithubService)
        issue = dict(body="A very short issue body.  Fixes #42.")
        self.assertEqual(issue["body"], service.body(issue))

    def test_body_newline_style(self):
        service = self.get_mock_service(GithubService)
        issue = dict(body="An\r\nIssue\r\nWith\r\nNewlines")
        self.assertEqual("An\nIssue\nWith\nNewlines", service.body(issue))

    def test_body_length_limit(self):
        service = self.get_mock_service(GithubService, config_overrides={
            'github.body_length': 5
        })
        issue = dict(body="A very short issue body.  Fixes #42.")
        self.assertEqual(issue["body"][:5], service.body(issue))


class TestGithubClient(TestCase):

    def test_api_url(self):
        auth = {'token': 'xxxx'}
        client = GithubClient('github.com', auth)
        self.assertEqual(
            client._api_url('/some/path'), 'https://api.github.com/some/path')

    def test_api_url_with_context(self):
        auth = {'token': 'xxxx'}
        client = GithubClient('github.com', auth)
        self.assertEqual(
            client._api_url('/some/path/{foo}', foo='bar'),
            'https://api.github.com/some/path/bar')

    def test_api_url_with_custom_host(self):
        """ Test generating an API URL with a custom host """
        auth = {'token': 'xxxx'}
        client = GithubClient('github.example.com', auth)
        self.assertEqual(
            client._api_url('/some/path'),
            'https://github.example.com/api/v3/some/path')
