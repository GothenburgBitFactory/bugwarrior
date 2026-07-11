from datetime import datetime, timedelta, timezone

import responses

from bugwarrior.collect import TaskConstructor
from bugwarrior.services.forgejo import ForgejoClient, ForgejoConfig, ForgejoService, ForgejoIssueReal, ForgejoPullRequest

from .base import ConfigTest, ServiceIssueTest, ServiceTest

ARBITRARY_CREATED = (datetime.now(timezone.utc) - timedelta(hours=1)).replace(
    microsecond=0
)
ARBITRARY_UPDATED = datetime.now(timezone.utc).replace(microsecond=0)
ARBITRARY_CLOSED = (datetime.now(timezone.utc) - timedelta(minutes=30)).replace(
    microsecond=0
)
ARBITRARY_DUE = (datetime.now(timezone.utc) + timedelta(days=1)).replace(
    microsecond=0
)
IGNORABLE = {'user': {'login': 'cibot'}, 'body': 'Ignore this comment.'}
ARBITRARY_USER = {
    'id': 12345,
    'login': 'arbitrary_login',
}
ARBITRARY_REPO = {
        'id': 4564778,
        'name': 'arbitrary_repo',
        'owner': 'arbitrary_username',
        'full_name': 'arbitrary_username/arbitrary_repo',
    }
ARBITRARY_ISSUE = {
    'title': 'Hallo',
    'html_url': 'https://codeberg.org/arbitrary_username/arbitrary_repo/issues/1',
    # PRs are called issues by the API
    'url': 'https://codeberg.org/api/v1/repos/arbitrary_username/arbitrary_repo/issues/1',
    'number': 10,
    'body': 'Something',
    'assignee': ARBITRARY_USER,
    'assignees': [ARBITRARY_USER],
    'user': ARBITRARY_USER,
    'milestone': {'title': 'alpha'},
    'labels': [{'id': 12, 'name': 'bugfix'}],
    'created_at': ARBITRARY_CREATED.isoformat(),
    'closed_at': ARBITRARY_CLOSED.isoformat(),
    'updated_at': ARBITRARY_UPDATED.isoformat(),
    'due_date': ARBITRARY_DUE.isoformat(),
    'state': 'open',
    'repository': ARBITRARY_REPO
}
ARBITRARY_PR = {
    'title': 'Hallo',
    'html_url': 'https://codeberg.org/arbitrary_username/arbitrary_repo/pulls/1',
    # PRs are called issues by the API
    'url': 'https://codeberg.org/api/v1/repos/arbitrary_username/arbitrary_repo/issues/1',
    'number': 10,
    'body': 'Something',
    'assignee': ARBITRARY_USER,
    'assignees': [ARBITRARY_USER],
    'user': ARBITRARY_USER,
    'milestone': {'title': 'alpha'},
    'labels': [{'id': 12, 'name': 'bugfix'}],
    'created_at': ARBITRARY_CREATED.isoformat(),
    'closed_at': ARBITRARY_CLOSED.isoformat(),
    'updated_at': ARBITRARY_UPDATED.isoformat(),
    'due_date': ARBITRARY_DUE.isoformat(),
    'state': 'closed',
    'draft': False,
    'pull_request': {
        'merged_at': ARBITRARY_CLOSED.isoformat(),
        'merged': True,
        'draft': False,
        'html_url': 'https://codeberg.org/arbitrary_username/arbitrary_repo/pulls/1',
    },
    'repository': ARBITRARY_REPO
}
ARBITRARY_EXTRA = {
    'project': 'one',
    'type': 'issue',
    'annotations': [],
    'body': 'Something',
    'namespace': 'arbitrary_username',
}


class TestForgejoIssue(ServiceIssueTest):
    SERVICE_CONFIG = {
        'service': 'forgejo',
        'host': 'codeberg.org',
        'token': 'arbitrary_token',
        'login': 'arbitrary_username',
        #'ignore_user_comments': [IGNORABLE['user']['login']],
    }

    def test_draft(self):
        service = self.get_mock_service(ForgejoService)
        draft = dict(ARBITRARY_PR)
        draft['pull_request']['draft'] = True
        issue = service.get_issue_for_record(draft, ARBITRARY_EXTRA)

        expected = {
            'annotations': [],
            'description': '(bw)Is#10 - Hallo .. https://codeberg.org/arbitrary_username/arbitrary_repo/pulls/1',  # noqa: E501
            'entry': ARBITRARY_CREATED,
            'end': ARBITRARY_CLOSED,
            'forgejobody': draft['body'],
            'forgejocreatedon': ARBITRARY_CREATED,
            'forgejoclosedon': ARBITRARY_CLOSED,
            'forgejodraft': int(draft['draft']),
            'forgejomilestone': draft['milestone']['title'],
            'forgejonamespace': draft['repository']['owner'],
            'forgejonumber': draft['number'],
            'forgejorepo': draft['repository']['full_name'],
            'forgejotitle': draft['title'],
            'forgejotype': 'issue',
            'forgejoupdatedat': ARBITRARY_UPDATED,
            'forgejourl': draft['html_url'],
            'forgejouser': draft['user']['login'],
            'forgejostate': draft['state'],
            'priority': 'M',
            'project': ARBITRARY_EXTRA['project'],
            'tags': ['bugfix'],
        }

        recorded = TaskConstructor(issue).get_taskwarrior_record()

        assert recorded == expected

    def test_to_taskwarrior(self):
        service = self.get_mock_service(
            ForgejoService, config_overrides={'import_labels_as_tags': True}
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
            issue.REPO: ARBITRARY_ISSUE['repository']['full_name'],
            issue.DRAFT: ARBITRARY_ISSUE.get('pull_request', {}).get("fdraft", 0),
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
            issue.STATE: ARBITRARY_ISSUE['state'],
        }
        actual_output = issue.to_taskwarrior()

        assert actual_output == expected_output

    @responses.activate
    def test_issues(self):
        responses.get(
            'https://codeberg.org/api/v1/user/repos?per_page=100',
            json=[{'name': 'some_repo', 'owner': {'login': 'some_username'}}],
        )

        responses.get(
            'https://codeberg.org/api/v1/users/arbitrary_username/repos?per_page=100',
            json=[{'name': 'arbitrary_repo', 'owner': {'login': 'arbitrary_username'}}],
        )

        responses.get(
            'https://codeberg.org/api/v1/repos/arbitrary_username/arbitrary_repo/issues?per_page=100',
            json=[ARBITRARY_ISSUE],
        )

        responses.get(
            'https://codeberg.org/api/v1/issues?per_page=100', json=[ARBITRARY_ISSUE]
        )

        responses.get(
            'https://codeberg.org/api/v1/repos/arbitrary_username/arbitrary_repo/issues/10/comments?per_page=100',  # noqa: E501
            json=[
                {'user': {'login': 'arbitrary_login'}, 'body': 'Arbitrary comment.'},
                IGNORABLE,
            ],
        )  # second comment should be ignored and still pass

        service = self.get_mock_service(ForgejoService)
        issue = next(service.issues())

        expected = {
            'annotations': ['@arbitrary_login - Arbitrary comment.'],
            'description': '(bw)Is#10 - Hallo .. https://codeberg.org/arbitrary_username/arbitrary_repo/pull/1',  # noqa: E501
            'entry': ARBITRARY_CREATED,
            'end': ARBITRARY_CLOSED,
            'forgejobody': 'Something',
            'forgejocreatedon': ARBITRARY_CREATED,
            'forgejoclosedon': ARBITRARY_CLOSED,
            'forgejodraft': 0,
            'forgejomilestone': 'alpha',
            'forgejonamespace': 'arbitrary_username',
            'forgejonumber': 10,
            'forgejorepo': 'arbitrary_username/arbitrary_repo',
            'forgejotitle': 'Hallo',
            'forgejotype': 'issue',
            'forgejoupdatedat': ARBITRARY_UPDATED,
            'forgejourl': 'https://codeberg.org/arbitrary_username/arbitrary_repo/pull/1',
            'forgejouser': 'arbitrary_login',
            'forgejostate': 'closed',
            'priority': 'M',
            'project': 'arbitrary_repo',
            'tags': [],
        }

        assert TaskConstructor(issue).get_taskwarrior_record() == expected


class TestForgejoIssueQuery(ServiceIssueTest):
    SERVICE_CONFIG = {
        'service': 'forgejo',
        'host': 'codeberg.org',
        'login': 'arbitrary_login',
        'token': 'arbitrary_token',
        'query': 'is:open reviewer:octocat',
        'include_user_repos': 'False',
        'include_user_issues': 'False',
    }

    def setUp(self):
        super().setUp()
        self.service = self.get_mock_service(ForgejoService)

    def test_to_taskwarrior(self):
        pass

    @responses.activate
    def test_issues(self):
        responses.get(
            'https://codeberg.org/api/v1/search/issues?q=is%3Aopen+reviewer%3Aoctocat&per_page=100',
            json={'items': [ARBITRARY_ISSUE]},
        )

        responses.get(
            'https://codeberg.org/api/v1/repos/arbitrary_username/arbitrary_repo/issues/10/comments?per_page=100',  # noqa: E501
            json=[{'user': {'login': 'arbitrary_login'}, 'body': 'Arbitrary comment.'}],
        )

        issue = list(self.service.issues())[0]

        expected = {
            'annotations': ['@arbitrary_login - Arbitrary comment.'],
            'description': '(bw)Is#10 - Hallo .. https://codeberg.org/arbitrary_username/arbitrary_repo/pull/1',  # noqa: E501
            'entry': ARBITRARY_CREATED,
            'end': ARBITRARY_CLOSED,
            'forgejobody': 'Something',
            'forgejocreatedon': ARBITRARY_CREATED,
            'forgejoclosedon': ARBITRARY_CLOSED,
            'forgejodraft': 0,
            'forgejomilestone': 'alpha',
            'forgejonamespace': 'arbitrary_username',
            'forgejonumber': 10,
            'forgejorepo': 'arbitrary_username/arbitrary_repo',
            'forgejotitle': 'Hallo',
            'forgejotype': 'issue',
            'forgejoupdatedat': ARBITRARY_UPDATED,
            'forgejourl': 'https://codeberg.org/arbitrary_username/arbitrary_repo/pull/1',
            'forgejouser': 'arbitrary_login',
            'forgejostate': 'closed',
            'priority': 'M',
            'project': 'arbitrary_repo',
            'tags': [],
        }

        assert TaskConstructor(issue).get_taskwarrior_record() == expected


class TestForgejoService(ServiceTest):
    SERVICE_CONFIG = {
        'service': 'forgejo',
        'login': 'tintin',
        'host': 'codeberg.org',
        'token': 't0ps3cr3t',
    }

    def test_token_authorization_header(self):
        service = self.get_mock_service(ForgejoService)
        service = self.get_mock_service(
            ForgejoService,
            config_overrides={'token': '@oracle:eval:echo 1234567890ABCDEF'},
        )
        assert (
            service.client.session.headers['Authorization'] == "token 1234567890ABCDEF"
        )

    def test_default_host(self):
        """Check that if host is not set, we default to codeberg.org"""
        service = self.get_mock_service(ForgejoService)
        assert "codeberg.org" == service.config.host

    def test_overwrite_host(self):
        """Check that if host is set, we use its value as host"""
        service = self.get_mock_service(
            ForgejoService, config_overrides={'host': 'forgejo.example.com'}
        )
        assert "forgejo.example.com" == service.config.host

    def test_keyring_service(self):
        """Checks that the keyring service name"""
        service_config = ForgejoConfig(**self.SERVICE_CONFIG, target="myservice")
        keyring_service = service_config.keyring_service
        assert "forgejo://tintin@codeberg.org/milou" == keyring_service

    def test_keyring_service_host(self):
        """Checks that the keyring key depends on the forgejo host."""
        service_config = ForgejoConfig(
            **self.SERVICE_CONFIG, target="myservice"
        )
        service_config.host = 'forgejo.example.com'
        keyring_service = service_config.keyring_service
        assert "forgejo://tintin@forgejo.example.com/milou" == keyring_service

    def test_get_repository_from_issue_url__issue(self):
        issue_dict = ARBITRARY_ISSUE
        issue_dict['html_url'] = "https://codeberg.org/foo/bar"
        issue = ForgejoIssueReal(**issue_dict)
        repository = ForgejoService.get_repository_from_issue(issue)
        assert "foo/bar" == repository

    def test_get_repository_from_issue_url__pull_request(self):
        issue_dict = ARBITRARY_ISSUE
        issue_dict['html_url'] = "https://codeberg.org/foo/bar"
        issue = ForgejoPullRequest(**issue_dict)
        repository = ForgejoService.get_repository_from_issue(issue)
        assert "foo/bar" == repository


class TestForgejoValidation(ConfigTest):
    SERVICE_CONFIG = {'service': 'forgejo', 'login': 'tintin', 'token': 't0ps3cr3t'}

    def setUp(self):
        super().setUp()
        self.config = {
            'general': {'targets': ['myservice']},
            'myservice': {**self.SERVICE_CONFIG, 'login': 'milou'},
        }

    def test_require_login_or_query(self):
        self.config['myservice']['include_user_repos'] = 'false'
        self.config['myservice'].pop('login')
        self.assertValidationError('section requires one of')

    def test_require_login_or_query_with_query(self):
        self.config['myservice']['include_user_repos'] = 'false'
        self.config['myservice'].pop('login')
        self.config['myservice']['query'] = 'is:open reviewer:octocat'
        self.validate()

    def test_require_login_if_include_user_repos_disabled(self):
        self.config['myservice'].pop('login')
        self.config['myservice']['query'] = 'is:open'
        self.config['myservice']['include_user_repos'] = 'false'
        self.validate()

    def test_issue_urls_consistent_with_host(self):
        self.config['myservice']['issue_urls'] = (
            'https://forgejo.example.com/foo/bar/issues/1'
        )
        self.assertValidationError('inconsistent with host')

    def test_issue_urls_invalid_path(self):
        self.config['myservice']['issue_urls'] = 'https://codeberg.org/foo/bar/invalid/1'
        self.assertValidationError('is not a valid issue path')

    def test_issue_urls_valid(self):
        self.config['myservice']['issue_urls'] = (
            'https://codeberg.org/foo/bar/issues/1, https://codeberg.org/foo/bar/pull/2'
        )
        self.validate()


class TestForgejoClient:
    def test_api_url(self):
        auth = 'xxxx'
        client = ForgejoClient('codeberg.org', auth)
        assert client._api_url('/some/path') == 'https://codeberg.org/api/v1/some/path'

    def test_api_url_with_context(self):
        auth = 'xxxx'
        client = ForgejoClient('codeberg.org', auth)
        assert (
            client._api_url('/some/path/{foo}', foo='bar')
            == 'https://codeberg.org/api/v1/some/path/bar'
        )

    def test_api_url_with_custom_host(self):
        """Test generating an API URL with a custom host"""
        auth = 'xxxx'
        client = ForgejoClient('forgejo.example.com', auth)
        assert (
            client._api_url('/some/path')
            == 'https://forgejo.example.com/api/v1/some/path'
        )
