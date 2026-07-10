from datetime import datetime, timedelta, timezone

import pytest
import responses

from bugwarrior.collect import TaskConstructor
from bugwarrior.services.github import GithubClient, GithubConfig, GithubService

from ..base import validate
from .base import get_mock_service

ARBITRARY_CREATED = (datetime.now(timezone.utc) - timedelta(hours=1)).replace(
    microsecond=0
)
ARBITRARY_CLOSED = (datetime.now(timezone.utc) - timedelta(minutes=30)).replace(
    microsecond=0
)
ARBITRARY_UPDATED = datetime.now(timezone.utc).replace(microsecond=0)
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
    'state': 'closed',
    'draft': False,
}
ARBITRARY_EXTRA = {
    'project': 'one',
    'type': 'issue',
    'annotations': [],
    'body': 'Something',
    'namespace': 'arbitrary_username',
}
IGNORABLE = {'user': {'login': 'cibot'}, 'body': 'Ignore this comment.'}


SERVICE_CONFIG = {
    'service': 'github',
    'login': 'arbitrary_login',
    'token': 'arbitrary_token',
    'username': 'arbitrary_username',
}


class TestGithubIssue:
    def test_draft(self):
        service = get_mock_service(GithubService, SERVICE_CONFIG)
        draft = dict(ARBITRARY_ISSUE)
        draft['draft'] = True
        issue = service.get_issue_for_record(draft, ARBITRARY_EXTRA)

        expected = {
            'annotations': [],
            'description': '(bw)Is#10 - Hallo .. https://github.com/arbitrary_username/arbitrary_repo/pull/1',  # noqa: E501
            'entry': ARBITRARY_CREATED,
            'end': ARBITRARY_CLOSED,
            'githubbody': draft['body'],
            'githubcreatedon': ARBITRARY_CREATED,
            'githubclosedon': ARBITRARY_CLOSED,
            'githubdraft': int(draft['draft']),
            'githubmilestone': draft['milestone']['title'],
            'githubnamespace': draft['repo'].split('/')[0],
            'githubnumber': draft['number'],
            'githubrepo': draft['repo'],
            'githubtitle': draft['title'],
            'githubtype': 'issue',
            'githubupdatedat': ARBITRARY_UPDATED,
            'githuburl': draft['html_url'],
            'githubuser': draft['user']['login'],
            'githubstate': draft['state'],
            'priority': 'M',
            'project': ARBITRARY_EXTRA['project'],
            'tags': [],
        }

        assert TaskConstructor(issue).get_taskwarrior_record() == expected

    def test_to_taskwarrior(self):
        service = get_mock_service(
            GithubService, {**SERVICE_CONFIG, 'import_labels_as_tags': True}
        )
        issue = service.get_issue_for_record(ARBITRARY_ISSUE, ARBITRARY_EXTRA)

        expected_output = {
            'project': ARBITRARY_EXTRA['project'],
            'priority': service.config.default_priority,
            'annotations': [],
            'tags': ['bugfix'],
            'entry': ARBITRARY_CREATED,
            'end': ARBITRARY_CLOSED,
            issue.URL: ARBITRARY_ISSUE['html_url'],
            issue.REPO: ARBITRARY_ISSUE['repo'],
            issue.DRAFT: ARBITRARY_ISSUE['draft'],
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

        assert actual_output == expected_output

    @responses.activate
    def test_issues(self):
        responses.get(
            'https://api.github.com/user/repos?per_page=100',
            json=[{'name': 'some_repo', 'owner': {'login': 'some_username'}}],
        )

        responses.get(
            'https://api.github.com/users/arbitrary_username/repos?per_page=100',
            json=[{'name': 'arbitrary_repo', 'owner': {'login': 'arbitrary_username'}}],
        )

        responses.get(
            'https://api.github.com/repos/arbitrary_username/arbitrary_repo/issues?per_page=100',
            json=[ARBITRARY_ISSUE],
        )

        responses.get(
            'https://api.github.com/issues?per_page=100', json=[ARBITRARY_ISSUE]
        )

        responses.get(
            'https://api.github.com/repos/arbitrary_username/arbitrary_repo/issues/10/comments?per_page=100',  # noqa: E501
            json=[
                {'user': {'login': 'arbitrary_login'}, 'body': 'Arbitrary comment.'},
                IGNORABLE,
            ],
        )  # second comment should be ignored and still pass

        service = get_mock_service(
            GithubService,
            {**SERVICE_CONFIG, 'ignore_user_comments': [IGNORABLE['user']['login']]},
        )
        issue = next(service.issues())

        expected = {
            'annotations': ['@arbitrary_login - Arbitrary comment.'],
            'description': '(bw)Is#10 - Hallo .. https://github.com/arbitrary_username/arbitrary_repo/pull/1',  # noqa: E501
            'entry': ARBITRARY_CREATED,
            'end': ARBITRARY_CLOSED,
            'githubbody': 'Something',
            'githubcreatedon': ARBITRARY_CREATED,
            'githubclosedon': ARBITRARY_CLOSED,
            'githubdraft': 0,
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
            'tags': [],
        }

        assert TaskConstructor(issue).get_taskwarrior_record() == expected


QUERY_SERVICE_CONFIG = {
    **SERVICE_CONFIG,
    'query': 'is:open reviewer:octocat',
    'include_user_repos': 'False',
    'include_user_issues': 'False',
}


class TestGithubIssueQuery:
    @pytest.fixture
    def service(self):
        return get_mock_service(GithubService, QUERY_SERVICE_CONFIG)

    def test_to_taskwarrior(self):
        pass

    @responses.activate
    def test_issues(self, service):
        responses.get(
            'https://api.github.com/search/issues?q=is%3Aopen+reviewer%3Aoctocat&per_page=100',
            json={'items': [ARBITRARY_ISSUE]},
        )

        responses.get(
            'https://api.github.com/repos/arbitrary_username/arbitrary_repo/issues/10/comments?per_page=100',  # noqa: E501
            json=[{'user': {'login': 'arbitrary_login'}, 'body': 'Arbitrary comment.'}],
        )

        issue = list(service.issues())[0]

        expected = {
            'annotations': ['@arbitrary_login - Arbitrary comment.'],
            'description': '(bw)Is#10 - Hallo .. https://github.com/arbitrary_username/arbitrary_repo/pull/1',  # noqa: E501
            'entry': ARBITRARY_CREATED,
            'end': ARBITRARY_CLOSED,
            'githubbody': 'Something',
            'githubcreatedon': ARBITRARY_CREATED,
            'githubclosedon': ARBITRARY_CLOSED,
            'githubdraft': 0,
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
            'tags': [],
        }

        assert TaskConstructor(issue).get_taskwarrior_record() == expected


class TestGithubService:
    def test_token_authorization_header(self):
        service = get_mock_service(GithubService, SERVICE_CONFIG)
        service = get_mock_service(
            GithubService,
            {**SERVICE_CONFIG, 'token': '@oracle:eval:echo 1234567890ABCDEF'},
        )
        assert (
            service.client.session.headers['Authorization'] == "token 1234567890ABCDEF"
        )

    def test_default_host(self):
        """Check that if host is not set, we default to github.com"""
        service = get_mock_service(GithubService, SERVICE_CONFIG)
        assert "github.com" == service.config.host

    def test_overwrite_host(self):
        """Check that if host is set, we use its value as host"""
        service = get_mock_service(
            GithubService, {**SERVICE_CONFIG, 'host': 'github.example.com'}
        )
        assert "github.example.com" == service.config.host

    def test_keyring_service(self):
        """Checks that the keyring service name"""
        service_config = GithubConfig(**SERVICE_CONFIG, target="myservice")
        keyring_service = service_config.keyring_service
        assert (
            "github://arbitrary_login@github.com/arbitrary_username" == keyring_service
        )

    def test_keyring_service_host(self):
        """Checks that the keyring key depends on the github host."""
        service_config = GithubConfig(
            **{'host': 'github.example.com'}, **SERVICE_CONFIG, target="myservice"
        )
        keyring_service = service_config.keyring_service
        assert (
            "github://arbitrary_login@github.example.com/arbitrary_username"
            == keyring_service
        )

    def test_get_repository_from_issue_url__issue(self):
        issue = dict(repos_url="https://github.com/foo/bar")
        repository = GithubService.get_repository_from_issue(issue)
        assert "foo/bar" == repository

    def test_get_repository_from_issue_url__pull_request(self):
        issue = dict(repos_url="https://github.com/foo/bar")
        repository = GithubService.get_repository_from_issue(issue)
        assert "foo/bar" == repository

    def test_get_repository_from_issue__enterprise_github(self):
        issue = dict(repos_url="https://github.acme.biz/foo/bar")
        repository = GithubService.get_repository_from_issue(issue)
        assert "foo/bar" == repository

    def test_body_no_limit(self):
        service = get_mock_service(GithubService, SERVICE_CONFIG)
        issue = dict(body="A very short issue body.  Fixes #42.")
        assert issue["body"] == service.body(issue)

    def test_body_newline_style(self):
        service = get_mock_service(GithubService, SERVICE_CONFIG)
        issue = dict(body="An\r\nIssue\r\nWith\r\nNewlines")
        assert "An\nIssue\nWith\nNewlines" == service.body(issue)

    def test_body_length_limit(self):
        service = get_mock_service(GithubService, {**SERVICE_CONFIG, 'body_length': 5})
        issue = dict(body="A very short issue body.  Fixes #42.")
        assert issue["body"][:5] == service.body(issue)


class TestGithubValidation:
    @pytest.fixture
    def config(self):
        return {'general': {'targets': ['myservice']}, 'myservice': {**SERVICE_CONFIG}}

    def test_require_username_or_query(self, config, assert_validation_error):
        config['myservice']['include_user_repos'] = 'false'
        config['myservice'].pop('username')
        assert_validation_error(config, 'section requires one of')

    def test_require_username_or_query_with_query(self, config):
        config['myservice']['include_user_repos'] = 'false'
        config['myservice'].pop('username')
        config['myservice']['query'] = 'is:open reviewer:octocat'
        validate(config)

    def test_require_username_if_include_user_repos(
        self, config, assert_validation_error
    ):
        config['myservice'].pop('username')
        config['myservice']['query'] = 'is:open'
        assert_validation_error(
            config, 'username required when include_user_repos is True'
        )

    def test_require_username_if_include_user_repos_disabled(self, config):
        config['myservice'].pop('username')
        config['myservice']['query'] = 'is:open'
        config['myservice']['include_user_repos'] = 'false'
        validate(config)

    def test_issue_urls_consistent_with_host(self, config, assert_validation_error):
        config['myservice']['issue_urls'] = (
            'https://github.example.com/foo/bar/issues/1'
        )
        assert_validation_error(config, 'inconsistent with host')

    def test_issue_urls_invalid_path(self, config, assert_validation_error):
        config['myservice']['issue_urls'] = 'https://github.com/foo/bar/invalid/1'
        assert_validation_error(config, 'is not a valid issue path')

    def test_issue_urls_valid(self, config):
        config['myservice']['issue_urls'] = (
            'https://github.com/foo/bar/issues/1, https://github.com/foo/bar/pull/2'
        )
        validate(config)


class TestGithubClient:
    def test_api_url(self):
        auth = {'token': 'xxxx'}
        client = GithubClient('github.com', auth)
        assert client._api_url('/some/path') == 'https://api.github.com/some/path'

    def test_api_url_with_context(self):
        auth = {'token': 'xxxx'}
        client = GithubClient('github.com', auth)
        assert (
            client._api_url('/some/path/{foo}', foo='bar')
            == 'https://api.github.com/some/path/bar'
        )

    def test_api_url_with_custom_host(self):
        """Test generating an API URL with a custom host"""
        auth = {'token': 'xxxx'}
        client = GithubClient('github.example.com', auth)
        assert (
            client._api_url('/some/path')
            == 'https://github.example.com/api/v3/some/path'
        )
