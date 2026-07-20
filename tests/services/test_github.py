from datetime import datetime, timedelta, timezone

import pytest
import responses

from bugwarrior.collect import TaskConstructor
from bugwarrior.services.github import GithubClient, GithubConfig, GithubService

from ..base import validate

IGNORABLE = {'user': {'login': 'cibot'}, 'body': 'Ignore this comment.'}

SERVICE_CLASS = GithubService

SERVICE_CONFIG = {
    'service': 'github',
    'login': 'arbitrary_login',
    'token': 'arbitrary_token',
    'username': 'arbitrary_username',
}


CREATED = (datetime.now(timezone.utc) - timedelta(hours=1)).replace(microsecond=0)
CLOSED = (datetime.now(timezone.utc) - timedelta(minutes=30)).replace(microsecond=0)
UPDATED = datetime.now(timezone.utc).replace(microsecond=0)


@pytest.fixture
def record():
    return {
        'title': 'Hallo',
        'html_url': 'https://github.com/arbitrary_username/arbitrary_repo/pull/1',
        'url': 'https://api.github.com/repos/arbitrary_username/arbitrary_repo/issues/1',
        'number': 10,
        'body': 'Something',
        'user': {'login': 'arbitrary_login'},
        'milestone': {'title': 'alpha'},
        'labels': [{'name': 'bugfix'}],
        'created_at': CREATED.isoformat(),
        'closed_at': CLOSED.isoformat(),
        'updated_at': UPDATED.isoformat(),
        'repo': 'arbitrary_username/arbitrary_repo',
        'state': 'closed',
        'draft': False,
    }


@pytest.fixture
def extra():
    return {
        'project': 'one',
        'type': 'issue',
        'annotations': [],
        'body': 'Something',
        'namespace': 'arbitrary_username',
    }


class TestGithubIssue:
    def test_draft(self, service, record, extra):
        record['draft'] = True
        issue = service.get_issue_for_record(record, extra)

        expected = {
            'annotations': [],
            'description': '(bw)Is#10 - Hallo .. https://github.com/arbitrary_username/arbitrary_repo/pull/1',  # noqa: E501
            'entry': CREATED,
            'end': CLOSED,
            'githubbody': record['body'],
            'githubcreatedon': CREATED,
            'githubclosedon': CLOSED,
            'githubdraft': int(record['draft']),
            'githubmilestone': record['milestone']['title'],
            'githubnamespace': record['repo'].split('/')[0],
            'githubnumber': record['number'],
            'githubrepo': record['repo'],
            'githubtitle': record['title'],
            'githubtype': 'issue',
            'githubupdatedat': UPDATED,
            'githuburl': record['html_url'],
            'githubuser': record['user']['login'],
            'githubstate': record['state'],
            'priority': 'M',
            'project': extra['project'],
            'tags': [],
        }

        assert TaskConstructor(issue).get_taskwarrior_record() == expected

    def test_to_taskwarrior(self, make_service, record, extra):
        service = make_service(import_labels_as_tags=True)
        issue = service.get_issue_for_record(record, extra)

        expected_output = {
            'project': extra['project'],
            'priority': service.config.default_priority,
            'annotations': [],
            'tags': ['bugfix'],
            'entry': CREATED,
            'end': CLOSED,
            issue.URL: record['html_url'],
            issue.REPO: record['repo'],
            issue.DRAFT: record['draft'],
            issue.TYPE: extra['type'],
            issue.TITLE: record['title'],
            issue.NUMBER: record['number'],
            issue.UPDATED_AT: UPDATED,
            issue.CREATED_AT: CREATED,
            issue.CLOSED_AT: CLOSED,
            issue.BODY: extra['body'],
            issue.MILESTONE: record['milestone']['title'],
            issue.USER: record['user']['login'],
            issue.NAMESPACE: 'arbitrary_username',
            issue.STATE: 'closed',
        }
        actual_output = issue.to_taskwarrior()

        assert actual_output == expected_output

    @responses.activate
    def test_issues(self, make_service, record):
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
            json=[record],
        )

        responses.get('https://api.github.com/issues?per_page=100', json=[record])

        responses.get(
            'https://api.github.com/repos/arbitrary_username/arbitrary_repo/issues/10/comments?per_page=100',  # noqa: E501
            json=[
                {'user': {'login': 'arbitrary_login'}, 'body': 'Arbitrary comment.'},
                IGNORABLE,
            ],
        )  # second comment should be ignored and still pass

        service = make_service(ignore_user_comments=[IGNORABLE['user']['login']])
        issue = next(service.issues())

        expected = {
            'annotations': ['@arbitrary_login - Arbitrary comment.'],
            'description': '(bw)Is#10 - Hallo .. https://github.com/arbitrary_username/arbitrary_repo/pull/1',  # noqa: E501
            'entry': CREATED,
            'end': CLOSED,
            'githubbody': 'Something',
            'githubcreatedon': CREATED,
            'githubclosedon': CLOSED,
            'githubdraft': 0,
            'githubmilestone': 'alpha',
            'githubnamespace': 'arbitrary_username',
            'githubnumber': 10,
            'githubrepo': 'arbitrary_username/arbitrary_repo',
            'githubtitle': 'Hallo',
            'githubtype': 'issue',
            'githubupdatedat': UPDATED,
            'githuburl': 'https://github.com/arbitrary_username/arbitrary_repo/pull/1',
            'githubuser': 'arbitrary_login',
            'githubstate': 'closed',
            'priority': 'M',
            'project': 'arbitrary_repo',
            'tags': [],
        }

        assert TaskConstructor(issue).get_taskwarrior_record() == expected


class TestGithubIssueQuery:
    @pytest.fixture
    def service(self, make_service):
        return make_service(
            query='is:open reviewer:octocat',
            include_user_repos='False',
            include_user_issues='False',
        )

    def test_to_taskwarrior(self):
        pass

    @responses.activate
    def test_issues(self, service, record):
        responses.get(
            'https://api.github.com/search/issues?q=is%3Aopen+reviewer%3Aoctocat&per_page=100',
            json={'items': [record]},
        )

        responses.get(
            'https://api.github.com/repos/arbitrary_username/arbitrary_repo/issues/10/comments?per_page=100',  # noqa: E501
            json=[{'user': {'login': 'arbitrary_login'}, 'body': 'Arbitrary comment.'}],
        )

        issue = list(service.issues())[0]

        expected = {
            'annotations': ['@arbitrary_login - Arbitrary comment.'],
            'description': '(bw)Is#10 - Hallo .. https://github.com/arbitrary_username/arbitrary_repo/pull/1',  # noqa: E501
            'entry': CREATED,
            'end': CLOSED,
            'githubbody': 'Something',
            'githubcreatedon': CREATED,
            'githubclosedon': CLOSED,
            'githubdraft': 0,
            'githubmilestone': 'alpha',
            'githubnamespace': 'arbitrary_username',
            'githubnumber': 10,
            'githubrepo': 'arbitrary_username/arbitrary_repo',
            'githubtitle': 'Hallo',
            'githubtype': 'issue',
            'githubupdatedat': UPDATED,
            'githuburl': 'https://github.com/arbitrary_username/arbitrary_repo/pull/1',
            'githubuser': 'arbitrary_login',
            'githubstate': 'closed',
            'priority': 'M',
            'project': 'arbitrary_repo',
            'tags': [],
        }

        assert TaskConstructor(issue).get_taskwarrior_record() == expected


class TestGithubService:
    def test_token_authorization_header(self, make_service):
        service = make_service(token='@oracle:eval:echo 1234567890ABCDEF')
        assert (
            service.client.session.headers['Authorization'] == "token 1234567890ABCDEF"
        )

    def test_default_host(self, service):
        """Check that if host is not set, we default to github.com"""
        assert "github.com" == service.config.host

    def test_overwrite_host(self, make_service):
        """Check that if host is set, we use its value as host"""
        service = make_service(host='github.example.com')
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

    def test_body_no_limit(self, service):
        issue = dict(body="A very short issue body.  Fixes #42.")
        assert issue["body"] == service.body(issue)

    def test_body_newline_style(self, service):
        issue = dict(body="An\r\nIssue\r\nWith\r\nNewlines")
        assert "An\nIssue\nWith\nNewlines" == service.body(issue)

    def test_body_length_limit(self, make_service):
        service = make_service(body_length=5)
        issue = dict(body="A very short issue body.  Fixes #42.")
        assert issue["body"][:5] == service.body(issue)


class TestGithubConfig:
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
