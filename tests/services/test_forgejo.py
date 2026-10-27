from datetime import UTC, datetime, timedelta

import pytest
import responses

from bugwarrior.services.forgejo import (
    INCOMPATIBLE_WITH_QUERY,
    ForgejoClient,
    ForgejoComment,
    ForgejoIssue,
    ForgejoLabel,
    ForgejoOrganization,
    ForgejoPrBranchInfo,
    ForgejoProcessedIssue,
    ForgejoPullRequest,
    ForgejoRepository,
    ForgejoRepositoryMeta,
    ForgejoService,
    ForgejoTeam,
    ForgejoTeamPermission,
    ForgejoUser,
    RepoName,
)

from ..base import validate

ARBITRARY_CLOSED = (datetime.now(UTC) - timedelta(minutes=30)).replace(microsecond=0)
ARBITRARY_CREATED = (datetime.now(UTC) - timedelta(hours=1)).replace(microsecond=0)
ARBITRARY_DUE = (datetime.now(UTC) + timedelta(days=1)).replace(microsecond=0)
ARBITRARY_UPDATED = datetime.now(UTC).replace(microsecond=0)

NEXT_ID = 0

SERVICE_CLASS = ForgejoService
SERVICE_NAME: str = "myforgejo"
SERVICE_CONFIG = {
    "service": "forgejo",
    "login": "tintin",
    "token": "t0ps3cr3t",
    "host": "https://codeberg.org",
}


def next_id() -> int:
    global NEXT_ID
    NEXT_ID += 1
    return NEXT_ID


def make_issue(
    *,
    host: str = "https://codeberg.org",
    user: dict | ForgejoUser,
    repository: dict | ForgejoRepositoryMeta,
    labels: list[dict] | None = None,
    is_pr: bool = False,
    **kwargs,
) -> ForgejoIssue:
    id = kwargs.get("id") or next_id()
    repo_issue_number = kwargs.get("number") or next_id()

    url_slug = "pulls" if is_pr else "issues"
    pull_request = None

    if is_pr:
        pull_request = {
            "merged": False,
            "merged_at": None,
            "draft": False,
            "html_url": f"{host}/{repository.full_name}/{url_slug}/{repo_issue_number}",
        }
    return ForgejoIssue.model_validate(
        {
            "id": id,
            "url": f"{host}/api/v1/repos/{repository.full_name}/{url_slug}/{repo_issue_number}",
            "html_url": f"{host}/{repository.full_name}/{url_slug}/{repo_issue_number}",
            "number": repo_issue_number,
            "user": user,
            # These are empty for non-pull-request issues
            "original_author": "",
            "original_author_id": 0,
            "title": "Example issue",
            "body": "This is the body of the issue",
            "ref": "",
            "assets": [],
            "labels": labels or [],
            "milestone": None,
            "assignee": None,
            "assignees": None,
            "state": "open",
            "is_locked": False,
            "comments": 0,
            "created_at": ARBITRARY_CREATED,
            "updated_at": ARBITRARY_UPDATED,
            "closed_at": None,
            "due_date": None,
            "pull_request": pull_request,
            "repository": repository,
            "pin_order": 0,
            **kwargs,
        }
    )


def make_pr(
    *,
    base_issue: ForgejoIssue,
    base_repository: ForgejoRepository,
    base_branch: ForgejoPrBranchInfo | None = None,
    head_branch: ForgejoPrBranchInfo | None = None,
    comments: int = 0,
    mergeable: bool = False,
    requested_reviewers: list[ForgejoUser] | None = None,
    requested_reviewers_teams: list[ForgejoUser] | None = None,
    review_comments: int = 0,
) -> ForgejoPullRequest:
    assert base_issue.repository.id == base_repository.id, (
        "sanity: issue and provided repo id should match"
    )
    assert base_issue.repository.name == base_repository.name, (
        "sanity: repository name should match in issue and provided repo"
    )
    assert base_issue.repository.full_name == base_repository.full_name, (
        "sanity: repository full name should match in issue and provided repo"
    )
    assert base_issue.repository.owner == base_repository.owner.login, (
        "sanity: repository owner should match in issue and provided repo"
    )

    return ForgejoPullRequest(
        id=base_issue.id,
        base=base_branch
        or ForgejoPrBranchInfo(
            repo=base_repository,
            repo_id=base_repository.id,
            sha="unchecked",
            label="",
            ref="feature-1",
        ),
        head=head_branch
        or ForgejoPrBranchInfo(
            repo=base_repository,
            repo_id=base_repository.id,
            sha="unchecked",
            label="",
            ref="feature-1",
        ),
        url=base_issue.url,
        number=base_issue.number,
        user=base_issue.user,
        title=base_issue.title,
        body=base_issue.body,
        labels=base_issue.labels,
        assignee=base_issue.assignee,
        assignees=base_issue.assignees,
        state=base_issue.state,
        draft=base_issue.pull_request.draft,
        comments=comments,
        html_url=base_issue.html_url,
        mergeable=mergeable,
        merged=base_issue.pull_request.merged,
        merged_at=base_issue.pull_request.merged_at,
        review_comments=review_comments,
        requested_reviewers=requested_reviewers or [],
        requested_reviewers_teams=requested_reviewers_teams or [],
    )


LABEL_BUG = ForgejoLabel(
    id=next_id(), name="bug", description="Something is not working", color="ee0701"
)
LABEL_ENHANCEMENT = ForgejoLabel(
    id=next_id(), name="enhancement", description="New feature", color="84b6eb"
)

SHARED_ORGANIZATION = ForgejoOrganization(
    id=next_id(),
    name="organization",
    full_name="Organization",
    username="org",
    email="unused",
)

LOGIN_USER = ForgejoUser(id=next_id(), login="login_user")
OTHER_USER = ForgejoUser(id=next_id(), login="other_user")
LOGIN_USER_TEAM = ForgejoTeam(
    id=next_id(),
    name="login team",
    description="login user's team",
    organization=SHARED_ORGANIZATION,
    permission=ForgejoTeamPermission.admin,
)

LOGIN_USER_REPO = ForgejoRepository(
    id=next_id(),
    name="login_user_repo",
    owner=LOGIN_USER,
    full_name=f"{LOGIN_USER.login}/login_user_repo",
    has_issues=True,
    has_pull_requests=False,
    has_projects=False,
    open_issues_count=1,
    open_pr_counter=0,
    private=False,
    topics=[],
)
LOGIN_USER_REPO_META = ForgejoRepositoryMeta(
    id=LOGIN_USER_REPO.id,
    name=LOGIN_USER_REPO.name,
    owner=LOGIN_USER_REPO.owner.login,
    full_name=LOGIN_USER_REPO.full_name,
)

OTHER_USER_REPO = ForgejoRepository(
    id=next_id(),
    name="login_user_repo",
    owner=OTHER_USER,
    full_name=f"{OTHER_USER.login}/login_user_repo",
    has_issues=True,
    has_pull_requests=False,
    has_projects=False,
    open_issues_count=1,
    open_pr_counter=0,
    private=False,
    topics=[],
)
OTHER_USER_REPO_META = ForgejoRepositoryMeta(
    id=OTHER_USER_REPO.id,
    name=OTHER_USER_REPO.name,
    owner=OTHER_USER_REPO.owner.login,
    full_name=OTHER_USER_REPO.full_name,
)

MENTIONED_ISSUE_COMMENTS = []
MENTIONED_PULL_ISSUE_COMMENTS = []
MENTIONED_PULL_REVIEW_COMMENTS = []
REVIEWED_PULL_REVIEW_COMMENTS = []
UNRELATED_ISSUE_COMMENTS = []
UNRELATED_PULL_ISSUE_COMMENTS = []
UNRELATED_PULL_REQUEST_COMMENTS = []

ASSIGNED_ISSUE = make_issue(
    user=OTHER_USER,
    repository=OTHER_USER_REPO_META,
    assignee=OTHER_USER,
    assignees=[OTHER_USER, LOGIN_USER],
)
CREATED_ISSUE = make_issue(user=LOGIN_USER, repository=OTHER_USER_REPO_META)
MENTIONED_ISSUE = make_issue(
    user=OTHER_USER,
    repository=OTHER_USER_REPO_META,
    comments=len(MENTIONED_ISSUE_COMMENTS),
)
USER_REPO_ISSUE = make_issue(user=OTHER_USER, repository=LOGIN_USER_REPO_META)
UNRELATED_ISSUE = make_issue(user=OTHER_USER, repository=OTHER_USER_REPO_META)

ASSIGNED_PULL_ISSUE = make_issue(
    user=LOGIN_USER,
    repository=LOGIN_USER_REPO_META,
    assignee=OTHER_USER,
    assignees=[OTHER_USER, LOGIN_USER],
    is_pr=True,
)
CREATED_PULL_ISSUE = make_issue(
    user=LOGIN_USER, repository=OTHER_USER_REPO_META, is_pr=True
)
MENTIONED_PULL_ISSUE = make_issue(
    user=OTHER_USER,
    repository=OTHER_USER_REPO_META,
    comments=len(MENTIONED_PULL_ISSUE_COMMENTS),
    is_pr=True,
)
USER_REPO_PULL_ISSUE = make_issue(
    user=OTHER_USER, repository=LOGIN_USER_REPO_META, is_pr=True
)
UNRELATED_PULL_ISSUE = make_issue(
    user=OTHER_USER, repository=OTHER_USER_REPO_META, is_pr=True
)
# These are the same as "unrelated" because the relevant data will be set in the associated
# ForgejoPullRequest
REVIEW_REQUESTED_PULL_ISSUE = make_issue(
    user=OTHER_USER, repository=LOGIN_USER_REPO_META, is_pr=True
)
REVIEW_REQUESTED_TEAM_PULL_ISSUE = make_issue(
    user=OTHER_USER, repository=OTHER_USER_REPO_META, is_pr=True
)
REVIEWED_PULL_ISSUE = make_issue(
    user=OTHER_USER, repository=OTHER_USER_REPO_META, is_pr=True
)

# Pull Request objects

ASSIGNED_PULL_REQUEST = make_pr(
    base_issue=ASSIGNED_PULL_ISSUE, base_repository=LOGIN_USER_REPO
)
CREATED_PULL_REQUEST = make_pr(
    base_issue=CREATED_PULL_ISSUE, base_repository=OTHER_USER_REPO
)
MENTIONED_PULL_REQUEST = make_pr(
    base_issue=MENTIONED_PULL_ISSUE, base_repository=OTHER_USER_REPO
)
MENTIONED_IN_REVIEW_PULL_REQUEST = make_pr(
    base_issue=UNRELATED_PULL_ISSUE, base_repository=OTHER_USER_REPO, review_comments=1
)
USER_REPO_PULL_REQUEST = make_pr(
    base_issue=USER_REPO_PULL_ISSUE, base_repository=LOGIN_USER_REPO
)
UNRELATED_PULL_REQUEST = make_pr(
    base_issue=UNRELATED_PULL_ISSUE, base_repository=OTHER_USER_REPO
)
REVIEW_REQUESTED_PULL_REQUEST = make_pr(
    base_issue=REVIEW_REQUESTED_PULL_ISSUE,
    base_repository=LOGIN_USER_REPO,
    requested_reviewers=[OTHER_USER, LOGIN_USER],
)
REVIEW_REQUESTED_TEAM_PULL_REQUEST = make_pr(
    base_issue=REVIEW_REQUESTED_TEAM_PULL_ISSUE,
    base_repository=OTHER_USER_REPO,
    requested_reviewers_teams=[LOGIN_USER_TEAM],
)
REVIEWED_PULL_REQUEST = make_pr(
    base_issue=REVIEWED_PULL_ISSUE,
    base_repository=OTHER_USER_REPO,
    review_comments=len(REVIEWED_PULL_REVIEW_COMMENTS),
)

# Processed objects
# These are tested to be correct below

ASSIGNED_PROCESSED_ISSUE = ForgejoProcessedIssue.from_issue(ASSIGNED_ISSUE, [])
CREATED_PROCESSED_ISSUE = ForgejoProcessedIssue.from_issue(CREATED_ISSUE, [])
MENTIONED_PROCESSED_ISSUE = ForgejoProcessedIssue.from_issue(
    MENTIONED_ISSUE, MENTIONED_ISSUE_COMMENTS
)
USER_REPO_PROCESSED_ISSUE = ForgejoProcessedIssue.from_issue(USER_REPO_ISSUE, [])
UNRELATED_PROCESSED_ISSUE = ForgejoProcessedIssue.from_issue(
    UNRELATED_ISSUE, UNRELATED_ISSUE_COMMENTS
)

ASSIGNED_PROCESSED_PULL_REQUEST = ForgejoProcessedIssue.from_pull_request(
    ASSIGNED_PULL_ISSUE, ASSIGNED_PULL_REQUEST, [], []
)
CREATED_PROCESSED_PULL_REQUEST = ForgejoProcessedIssue.from_pull_request(
    CREATED_PULL_ISSUE, CREATED_PULL_REQUEST, [], []
)
MENTIONED_PROCESSED_PULL_REQUEST = ForgejoProcessedIssue.from_pull_request(
    MENTIONED_PULL_ISSUE, MENTIONED_PULL_REQUEST, MENTIONED_PULL_ISSUE_COMMENTS, []
)
MENTIONED_IN_REVIEW_PROCESSED_PULL_REQUEST = ForgejoProcessedIssue.from_pull_request(
    UNRELATED_PULL_ISSUE,
    MENTIONED_IN_REVIEW_PULL_REQUEST,
    [],
    MENTIONED_PULL_REVIEW_COMMENTS,
)
USER_REPO_PROCESSED_PULL_REQUEST = ForgejoProcessedIssue.from_pull_request(
    USER_REPO_PULL_ISSUE, USER_REPO_PULL_REQUEST, [], []
)
UNRELATED_PROCESSED_PULL_REQUEST = ForgejoProcessedIssue.from_pull_request(
    UNRELATED_PULL_ISSUE,
    UNRELATED_PULL_REQUEST,
    UNRELATED_PULL_ISSUE_COMMENTS,
    UNRELATED_PULL_REQUEST_COMMENTS,
)
REVIEW_REQUESTED_PROCESSED_PULL_REQUEST = ForgejoProcessedIssue.from_pull_request(
    REVIEW_REQUESTED_PULL_ISSUE, REVIEW_REQUESTED_PULL_REQUEST, [], []
)
REVIEW_REQUESTED_TEAM_PROCESSED_PULL_REQUEST = ForgejoProcessedIssue.from_pull_request(
    REVIEW_REQUESTED_TEAM_PULL_ISSUE, REVIEW_REQUESTED_TEAM_PULL_REQUEST, [], []
)
REVIEWED_PROCESSED_PULL_REQUEST = ForgejoProcessedIssue.from_pull_request(
    REVIEWED_PULL_ISSUE, REVIEWED_PULL_REQUEST, [], REVIEWED_PULL_REVIEW_COMMENTS
)


# class TestForgejoIssueImpl(ServiceIssueTest):
#    SERVICE_CONFIG = {
#        'service': 'forgejo',
#        'host': 'https://codeberg.org',
#        'token': 'arbitrary_token',
#        'login': 'arbitrary_username',
#        'issue_limit': 50,
#        #'ignore_user_comments': [IGNORABLE['user']['login']],
#    }
#
#    def test_draft(self):
#        service = self.get_mock_service(ForgejoService)
#        draft = dict(ARBITRARY_PR)
#        draft['pull_request']['draft'] = True
#        issue = service.get_issue_for_record(draft, ARBITRARY_EXTRA)
#
#        expected = {
#            'annotations': [],
#            'description': '(bw)Is#10 - Hallo .. https://codeberg.org/arbitrary_username/arbitrary_repo/pulls/1',  # noqa: E501
#            'entry': ARBITRARY_CREATED,
#            'end': ARBITRARY_CLOSED,
#            issue.BODY: draft['body'],
#            issue.CREATED_AT: ARBITRARY_CREATED,
#            issue.CLOSED_AT: ARBITRARY_CLOSED,
#            issue.DRAFT: int(draft['draft']),
#            issue.MILESTONE: draft['milestone']['title'],
#            issue.NAMESPACE: draft['repository']['owner'],
#            issue.NUMBER: draft['number'],
#            issue.REPO: draft['repository']['full_name'],
#            issue.TITLE: draft['title'],
#            issue.TYPE: 'issue',
#            issue.UPDATED_AT: ARBITRARY_UPDATED,
#            issue.URL: draft['html_url'],
#            issue.USER: draft['user']['login'],
#            issue.STATE: draft['state'],
#            'priority': 'M',
#            'project': ARBITRARY_EXTRA['project'],
#            'tags': ['bugfix'],
#        }
#
#        recorded = TaskConstructor(issue).get_taskwarrior_record()
#
#        assert recorded == expected
#
#    def test_to_taskwarrior(self):
#        service = self.get_mock_service(
#            ForgejoService, config_overrides={'import_labels_as_tags': True}
#        )
#        issue = service.get_issue_for_record(ARBITRARY_ISSUE, ARBITRARY_EXTRA)
#
#        expected_output = {
#            'project': ARBITRARY_EXTRA['project'],
#            'priority': service.config.default_priority,
#            'annotations': [],
#            'tags': ['bugfix'],
#            'entry': ARBITRARY_CREATED,
#            'end': ARBITRARY_CLOSED,
#            issue.URL: ARBITRARY_ISSUE['html_url'],
#            issue.REPO: ARBITRARY_ISSUE['repository']['full_name'],
#            issue.DRAFT: (ARBITRARY_ISSUE.get('pull_request') or {}).get("draft", 0),
#            issue.TYPE: ARBITRARY_EXTRA['type'],
#            issue.TITLE: ARBITRARY_ISSUE['title'],
#            issue.NUMBER: ARBITRARY_ISSUE['number'],
#            issue.UPDATED_AT: ARBITRARY_UPDATED,
#            issue.CREATED_AT: ARBITRARY_CREATED,
#            issue.CLOSED_AT: ARBITRARY_CLOSED,
#            issue.BODY: ARBITRARY_EXTRA['body'],
#            issue.MILESTONE: ARBITRARY_ISSUE['milestone']['title'],
#            issue.USER: ARBITRARY_ISSUE['user']['login'],
#            issue.NAMESPACE: 'arbitrary_username',
#            issue.STATE: ARBITRARY_ISSUE['state'],
#        }
#        actual_output = issue.to_taskwarrior()
#
#        assert actual_output == expected_output
#
#    @responses.activate
#    def test_issues(self):
#        responses.get('https://codeberg.org/api/v1/user/repos', json=[ARBITRARY_REPO])
#
#        responses.get(
#            'https://codeberg.org/api/v1/users/arbitrary_username/repos',
#            json=[ARBITRARY_REPO],
#        )
#
#        responses.get(
#            'https://codeberg.org/api/v1/repos/arbitrary_username/arbitrary_repo/issues',
#            json=[ARBITRARY_ISSUE],
#        )
#
#        responses.get(
#            f'https://codeberg.org/api/v1/repos/issues/search?limit={self.SERVICE_CONFIG["issue_limit"]}&created=true&',
#            json=[ARBITRARY_ISSUE],
#        )
#
#        responses.get(
#            'https://codeberg.org/api/v1/repos/arbitrary_username/arbitrary_repo/issues/10/comments',  # noqa: E501
#            json=[
#                {'user': {'login': 'arbitrary_login'}, 'body': 'Arbitrary comment.'},
#                IGNORABLE,
#            ],
#        )  # second comment should be ignored and still pass
#
#        service = self.get_mock_service(ForgejoService)
#        issue = next(service.issues())
#
#        expected = {
#            'annotations': ['@arbitrary_login - Arbitrary comment.'],
#            'description': '(bw)Is#10 - Hallo .. https://codeberg.org/arbitrary_username/arbitrary_repo/pull/1',  # noqa: E501
#            'entry': ARBITRARY_CREATED,
#            'end': ARBITRARY_CLOSED,
#            issue.BODY: 'Something',
#            issue.CREATED_AT: ARBITRARY_CREATED,
#            issue.CLOSED_AT: ARBITRARY_CLOSED,
#            issue.DRAFT: 0,
#            issue.MILESTONE: 'alpha',
#            issue.NAMESPACE: 'arbitrary_username',
#            issue.NUMBER: 10,
#            issue.REPO: 'arbitrary_username/arbitrary_repo',
#            issue.TITLE: 'Hallo',
#            issue.TYPE: 'issue',
#            issue.UPDATED_AT: ARBITRARY_UPDATED,
#            issue.URL: 'https://codeberg.org/arbitrary_username/arbitrary_repo/pull/1',
#            issue.USER: 'arbitrary_login',
#            issue.STATE: 'closed',
#            'priority': 'M',
#            'project': 'arbitrary_repo',
#            'tags': [],
#        }
#
#        assert TaskConstructor(issue).get_taskwarrior_record() == expected


# class TestForgejoIssueQuery(ServiceIssueTest):
#    SERVICE_CONFIG = {
#        'service': 'forgejo',
#        'host': 'https://codeberg.org',
#        'login': 'arbitrary_login',
#        'token': 'arbitrary_token',
#        'query': 'is:open author:arbitrary_login',
#    }
#
#    def setUp(self):
#        super().setUp()
#        self.service = self.get_mock_service(ForgejoService)
#
#    def test_to_taskwarrior(self):
#        pass
#
#    @responses.activate
#    def test_issues(self):
#        responses.get(
#            'https://codeberg.org/api/v1/search/issues?q=is%3Aopen+author%3Aarbitrary_login',
#            json={'items': [ARBITRARY_ISSUE]},
#            match=[matchers.header_matcher({"Authorization": "token arbitrary_token"})],
#        )
#
#        responses.get(
#            'https://codeberg.org/api/v1/repos/arbitrary_username/arbitrary_repo/issues/10/comments',  # noqa: E501
#            json=[{'user': {'login': 'arbitrary_login'}, 'body': 'Arbitrary comment.'}],
#            match=[matchers.header_matcher({"Authorization": "token arbitrary_token"})],
#        )
#
#        issue = list(self.service.issues())[0]
#
#        expected = {
#            'annotations': ['@arbitrary_login - Arbitrary comment.'],
#            'description': '(bw)Is#10 - Hallo .. https://codeberg.org/arbitrary_username/arbitrary_repo/pull/1',  # noqa: E501
#            'entry': ARBITRARY_CREATED,
#            'end': ARBITRARY_CLOSED,
#            issue.BODY: 'Something',
#            issue.CREATED_AT: ARBITRARY_CREATED,
#            issue.CLOSED_AT: ARBITRARY_CLOSED,
#            issue.DRAFT: 0,
#            issue.MILESTONE: 'alpha',
#            issue.NAMESPACE: 'arbitrary_username',
#            issue.NUMBER: 10,
#            issue.REPO: 'arbitrary_username/arbitrary_repo',
#            issue.TITLE: 'Hallo',
#            issue.TYPE: 'issue',
#            issue.UPDATED_AT: ARBITRARY_UPDATED,
#            issue.URL: 'https://codeberg.org/arbitrary_username/arbitrary_repo/pull/1',
#            issue.USER: 'arbitrary_login',
#            issue.STATE: 'closed',
#            'priority': 'M',
#            'project': 'arbitrary_repo',
#            'tags': [],
#        }
#
#        assert TaskConstructor(issue).get_taskwarrior_record() == expected
#
#
# class TestForgejoService(ServiceTest):
#    SERVICE_CONFIG = {
#        'service': 'forgejo',
#        'login': 'tintin',
#        'host': 'https://codeberg.org',
#        'token': 't0ps3cr3t',
#    }
#
#    def test_token_authorization_header(self):
#        service = self.get_mock_service(ForgejoService)
#        service = self.get_mock_service(
#            ForgejoService,
#            config_overrides={'token': '@oracle:eval:echo 1234567890ABCDEF'},
#        )
#        assert (
#            service.client.session.headers['Authorization'] == "token 1234567890ABCDEF"
#        )
#
#    def test_keyring_service(self):
#        """Checks that the keyring service name"""
#        service_config = ForgejoConfig(**self.SERVICE_CONFIG, target="myservice")
#        keyring_service = service_config.keyring_service
#        assert "forgejo://tintin@https://codeberg.org" == keyring_service
#
#    def test_keyring_service_host(self):
#        """Checks that the keyring key depends on the forgejo host."""
#        config = copy(self.SERVICE_CONFIG)
#        config['host'] = 'https://forgejo.example.com'
#        service_config = ForgejoConfig(**config, target="myservice")
#        keyring_service = service_config.keyring_service
#        assert "forgejo://tintin@https://forgejo.example.com" == keyring_service
#
#    def test_get_repository_from_issue_url__issue(self):
#        issue_dict = ARBITRARY_ISSUE
#        issue_dict['html_url'] = "https://codeberg.org/foo/bar/issues/42"
#        issue = ForgejoIssueReal(**issue_dict)
#        repository = ForgejoService.get_repository_from_issue(issue)
#        assert RepoName.from_tag("foo/bar") == repository
#
#    def test_get_repository_from_issue_url__pull_request(self):
#        issue_dict = ARBITRARY_PR
#        issue_dict['html_url'] = "https://codeberg.org/foo/bar/pulls/23"
#        issue = ForgejoPullRequest(**issue_dict)
#        repository = ForgejoService.get_repository_from_issue(issue)
#        assert RepoName.from_tag("foo/bar") == repository


class TestRepoName:
    def test_from_tag(self):
        input = "foo/bar"
        expected = RepoName("foo", "bar")
        parsed = RepoName.from_tag(input)
        assert parsed == expected, "parsed repo name did not match expectation"

    def test_str(self):
        input = "foo/bar"
        parsed = RepoName("foo", "bar")
        assert str(parsed) == input, "serialized repo name did not match expectation"


class TestForgejoProcessedIssue:
    @staticmethod
    def assert_matches_issue(
        processed: ForgejoProcessedIssue,
        issue: ForgejoIssue,
        comments: list[ForgejoComment],
    ):
        assert processed.id == issue.id, "issue id did not match"
        assert processed.number == issue.number, "issue number did not match"
        assert processed.assignees == issue.assignees, "issue assigness did not match"
        assert processed.body == issue.body, "issue body did not match"
        assert processed.closed_at == issue.closed_at, (
            "issue closing date did not match"
        )
        assert processed.created_at == issue.created_at, (
            "issue creation date did not match"
        )
        assert processed.due_date == issue.due_date, "issue due date did not match"
        assert processed.labels == issue.labels, "issue labels did not match"
        assert processed.milestone == issue.milestone, "issue milestone did not match"
        assert processed.repository == issue.repository, "issue repo meta did not match"
        assert processed.state == issue.state, "issue state did not match"
        assert processed.title == issue.title, "issue title did not match"
        assert processed.updated_at == issue.updated_at, (
            "issue updated date did not match"
        )
        assert processed.api_url == issue.url, "issue api url did not match"
        assert processed.html_url == issue.html_url, "issue html url did not match"
        assert processed.user == issue.user, "issue user did not match"
        assert len(processed.comments) == issue.comments, (
            "issue comment count did not match"
        )
        assert processed.comments == comments, "issue comments did not match"

        if issue.pull_request is None:
            assert not processed.is_pull_request, "non-pr issue was flagged as pr"
            assert not processed.is_draft_pr, "non-pr issue cannot be draft"
            assert processed.pr_review_comments is None, (
                "non-pr issue cannot have review comments"
            )
            assert processed.pr_base_branch is None, (
                "non-pr issue cannot have base branch"
            )
            assert processed.pr_merged_at is None, "non-pr issue cannot have merge date"
            assert processed.pr_is_mergeable is None, "non-pr issue cannot be mergeable"
            assert not processed.pr_requested_reviewers, (
                "non-pr issue cannot have reviewers"
            )
            assert not processed.pr_requested_reviewers_teams, (
                "non-pr issue cannot have reviewer teams"
            )
        else:
            assert processed.is_pull_request, (
                "pull request issue was not marked as pull request"
            )
            assert processed.is_draft_pr == issue.pull_request.draft, (
                "pull request draft status mismatch"
            )
            assert processed.pr_merged_at == issue.pull_request.merged_at, (
                "pull request merge date mismatch"
            )
            # This branch has fewer checks because the other fields should be checked
            # by assert_matches_pull_request

    @staticmethod
    def assert_matches_pull_request(
        processed: ForgejoProcessedIssue,
        issue: ForgejoIssue,
        pr: ForgejoPullRequest,
        issue_comments: list[ForgejoComment],
        review_comments: list[ForgejoComment],
    ):
        TestForgejoProcessedIssue.assert_matches_issue(processed, issue, issue_comments)
        assert processed.id == pr.id, "pull request id mismatch"
        assert processed.api_url == pr.url, "pull request api url mismatch"
        assert processed.number == pr.number, "pull request number mismatch"
        assert processed.user == pr.user, "pull request user mismatch"
        assert processed.title == pr.title, "pull request title mismatch"
        assert processed.body == pr.body, "pull request body mismatch"
        assert processed.labels == pr.labels, "pull request labels mismatch"
        assert processed.assignees == pr.assignees, "pull request assignees mismatch"
        assert processed.pr_requested_reviewers == pr.requested_reviewers, (
            "pull request reviewers mismatch"
        )
        assert processed.pr_requested_reviewers_teams == pr.requested_reviewers_teams, (
            "pull request reviewer teams mismatch"
        )
        assert processed.state == pr.state, "pull request state mismatch"
        assert processed.is_draft_pr == pr.draft, "pull request draft status mismatch"
        assert len(processed.comments) == pr.comments, (
            "pull request comment count mismatch"
        )
        assert processed.comments == issue_comments, "pull request comments mismatch"
        assert len(processed.pr_review_comments) == pr.review_comments, (
            "pull request review comment count mismatch"
        )
        assert processed.pr_review_comments == review_comments, (
            "pull request review comments mismatch"
        )
        assert processed.html_url == pr.html_url, "pull request html url mismatch"
        assert processed.pr_is_mergeable == pr.mergeable, (
            "pull request mergeability mismatch"
        )
        assert processed.is_merged_pr == pr.merged, (
            "pull request merged status mismatch"
        )
        assert processed.pr_merged_at == pr.merged_at, (
            "pull request merge date mismatch"
        )
        assert processed.pr_base_branch == pr.base, "pull request base branch mismatch"

    @pytest.mark.parametrize(
        ("expected", "issue", "comments"),
        [
            (ASSIGNED_PROCESSED_ISSUE, ASSIGNED_ISSUE, []),
            (CREATED_PROCESSED_ISSUE, CREATED_ISSUE, []),
            (MENTIONED_PROCESSED_ISSUE, MENTIONED_ISSUE, MENTIONED_ISSUE_COMMENTS),
            (USER_REPO_PROCESSED_ISSUE, USER_REPO_ISSUE, []),
            (UNRELATED_PROCESSED_ISSUE, UNRELATED_ISSUE, UNRELATED_ISSUE_COMMENTS),
        ],
        ids=["assigned", "created", "mentioned", "user_repo", "unrelated"],
    )
    def test_from_issue(
        self,
        expected: ForgejoProcessedIssue,
        issue: ForgejoIssue,
        comments: list[ForgejoComment],
    ):
        processed = ForgejoProcessedIssue.from_issue(issue, comments)
        assert processed == expected, "processed issue did not match expectation"
        TestForgejoProcessedIssue.assert_matches_issue(processed, issue, comments)

    @pytest.mark.parametrize(
        ("expected", "issue", "pull_request", "issue_comments", "review_comments"),
        [
            (
                ASSIGNED_PROCESSED_PULL_REQUEST,
                ASSIGNED_PULL_ISSUE,
                ASSIGNED_PULL_REQUEST,
                [],
                [],
            ),
            (
                CREATED_PROCESSED_PULL_REQUEST,
                CREATED_PULL_ISSUE,
                CREATED_PULL_REQUEST,
                [],
                [],
            ),
            (
                MENTIONED_PROCESSED_PULL_REQUEST,
                MENTIONED_PULL_ISSUE,
                MENTIONED_PULL_REQUEST,
                MENTIONED_PULL_ISSUE_COMMENTS,
                [],
            ),
            (
                UNRELATED_PROCESSED_PULL_REQUEST,
                UNRELATED_PULL_ISSUE,
                MENTIONED_IN_REVIEW_PULL_REQUEST,
                [],
                MENTIONED_PULL_REVIEW_COMMENTS,
            ),
            (
                USER_REPO_PROCESSED_PULL_REQUEST,
                USER_REPO_PULL_ISSUE,
                USER_REPO_PULL_REQUEST,
                [],
                [],
            ),
            (
                UNRELATED_PROCESSED_PULL_REQUEST,
                UNRELATED_PULL_ISSUE,
                UNRELATED_PULL_REQUEST,
                [],
                [],
            ),
            (
                REVIEW_REQUESTED_PROCESSED_PULL_REQUEST,
                REVIEW_REQUESTED_PULL_ISSUE,
                REVIEW_REQUESTED_PULL_REQUEST,
                [],
                [],
            ),
            (
                REVIEW_REQUESTED_TEAM_PROCESSED_PULL_REQUEST,
                REVIEW_REQUESTED_TEAM_PULL_ISSUE,
                REVIEW_REQUESTED_TEAM_PULL_REQUEST,
                [],
                [],
            ),
            (
                REVIEWED_PROCESSED_PULL_REQUEST,
                REVIEWED_PULL_ISSUE,
                REVIEWED_PULL_REQUEST,
                [],
                REVIEWED_PULL_REVIEW_COMMENTS,
            ),
        ],
        ids=[
            "assigned",
            "created",
            "mentioned",
            "mentioned_unrelated",
            "userrepo",
            "unrelated",
            "review_requested",
            "review_team_requested",
            "reviewed",
        ],
    )
    def test_from_pull_request(
        self,
        expected: ForgejoProcessedIssue,
        issue: ForgejoIssue,
        pull_request: ForgejoPullRequest,
        issue_comments: list[ForgejoComment],
        review_comments: list[ForgejoComment],
    ):
        processed = ForgejoProcessedIssue.from_pull_request(
            issue, pull_request, issue_comments, review_comments
        )
        assert processed == expected, "processed pull request did not match expected"
        TestForgejoProcessedIssue.assert_matches_pull_request(
            processed, issue, pull_request, issue_comments, review_comments
        )


class TestForgejoConfigValidation:
    @pytest.fixture
    def config(self):
        return {
            "general": {"targets": [SERVICE_NAME]},
            SERVICE_NAME: {**SERVICE_CONFIG},
        }

    def test_host_must_contain_https(self, config, assert_validation_error):
        config[SERVICE_NAME]["host"] = "codeberg.org"
        assert_validation_error(config, 'should use the "https" scheme')
        config[SERVICE_NAME]["host"] = "http://codeberg.org"
        assert_validation_error(config, 'should use the "https" scheme')
        config[SERVICE_NAME]["host"] = "https://codeberg.org"
        validate(config)

    def test_host_must_contain_hostname(self, config, assert_validation_error):
        config[SERVICE_NAME]["host"] = "https:///path/to/file"
        assert_validation_error(config, "must contain a hostname")
        config[SERVICE_NAME]["host"] = "https://codeberg.org"
        validate(config)

    def test_repo_cannot_be_in_both_include_and_exclude(
        self, config, assert_validation_error
    ):
        config[SERVICE_NAME]["include_repos"] = "foo/bar, foo/baz"
        config[SERVICE_NAME]["exclude_repos"] = "foo/baz, foo/quux"
        assert_validation_error(
            config,
            "one or more repos appear in both include_repos and exclude_repos: {'foo/baz'}",
        )

    @pytest.mark.parametrize("field", INCOMPATIBLE_WITH_QUERY)
    def test_disallow_field_if_query_is_set(
        self, config, assert_validation_error, field: str
    ):
        config[SERVICE_NAME]["query"] = "is:open"
        config[SERVICE_NAME][field] = True
        assert_validation_error(config, 'are incompatible with "query"')

    def test_issue_urls_consistent_with_host(self, config, assert_validation_error):
        config[SERVICE_NAME]["host"] = "https://codeberg.org"
        config[SERVICE_NAME]["issue_urls"] = (
            "https://forgejo.example.com/foo/bar/issues/1"
        )
        assert_validation_error(config, "inconsistent with the configured host")

    def test_issue_urls_invalid(self, config, assert_validation_error):
        config[SERVICE_NAME]["issue_urls"] = "https://codeberg.org/foo/bar/invalid/1"
        assert_validation_error(config, "is not a valid issue or pull request url")

    def test_issue_urls_valid(self, config):
        config[SERVICE_NAME]["issue_urls"] = (
            "https://codeberg.org/foo/bar/issues/1, https://codeberg.org/foo/bar/pulls/2"
        )
        validate(config)

    @pytest.mark.parametrize(
        ("config_name", "issue"),
        [
            ("include_assigned_issues", ASSIGNED_ISSUE),
            ("include_assigned_issues", ASSIGNED_PULL_REQUEST),
            ("include_created_issues", CREATED_ISSUE),
            ("include_created_issues", CREATED_PULL_REQUEST),
            ("include_mentioned_issues", MENTIONED_ISSUE),
            ("include_mentioned_issues", MENTIONED_PULL_REQUEST),
            ("include_mentioned_issues", MENTIONED_IN_REVIEW_PULL_REQUEST),
            ("include_user_repos", USER_REPO_ISSUE),
            ("include_user_repos", USER_REPO_PULL_REQUEST),
            ("include_review_requested_issues", REVIEW_REQUESTED_PULL_REQUEST),
            ("include_review_requested_issues", REVIEW_REQUESTED_TEAM_PULL_REQUEST),
            ("include_reviewed_issues", REVIEWED_PULL_REQUEST),
        ],
    )
    def test_issue_kept_if_related_config_enabled(
        self, config, make_service, config_name: str, issue: ForgejoIssue
    ):
        config[SERVICE_NAME]["filter_pull_requests"] = True
        config[SERVICE_NAME][config_name] = True
        assert make_service(**config[SERVICE_NAME]).parsed_config.filter_issue(issue), (
            f"issue should be kept when {config_name} enabled"
        )
        config[SERVICE_NAME][config_name] = False
        assert not make_service(**config[SERVICE_NAME]).parsed_config.filter_issue(
            issue
        ), f"issue should not be kept when {config_name} disabled"

    @pytest.mark.parametrize(
        ("config_name", "issue"),
        [
            ("include_assigned_issues", ASSIGNED_PULL_REQUEST),
            ("include_created_issues", CREATED_PULL_REQUEST),
            ("include_mentioned_issues", MENTIONED_PULL_REQUEST),
            ("include_mentioned_issues", MENTIONED_IN_REVIEW_PULL_REQUEST),
            ("include_user_repos", USER_REPO_PULL_REQUEST),
            (
                "include_review_requested_issues",
                REVIEW_REQUESTED_PULL_REQUEST,
            ),
            (
                "include_review_requested_issues",
                REVIEW_REQUESTED_TEAM_PULL_REQUEST,
            ),
            ("include_reviewed_issues", REVIEWED_PULL_REQUEST),
            ("", UNRELATED_PULL_REQUEST),
        ],
    )
    def test_pull_request_kept_if_not_filtered(
        self, config, make_service, config_name: str, issue: ForgejoIssue
    ):
        if config_name:
            config[SERVICE_NAME][config_name] = False
        config[SERVICE_NAME]["filter_pull_requests"] = False
        assert make_service(**config[SERVICE_NAME]).parsed_config.filter_issue(issue), (
            "pull request should be kept when not filtered"
        )

    @pytest.mark.parametrize(
        ("config_name", "issue"),
        [
            ("include_assigned_issues", ASSIGNED_PULL_REQUEST),
            ("include_created_issues", CREATED_PULL_REQUEST),
            ("include_mentioned_issues", MENTIONED_PULL_REQUEST),
            ("include_mentioned_issues", MENTIONED_IN_REVIEW_PULL_REQUEST),
            ("include_user_repos", USER_REPO_PULL_REQUEST),
            (
                "include_review_requested_issues",
                REVIEW_REQUESTED_PULL_REQUEST,
            ),
            (
                "include_review_requested_issues",
                REVIEW_REQUESTED_TEAM_PULL_REQUEST,
            ),
            ("include_reviewed_issues", REVIEWED_PULL_REQUEST),
        ],
    )
    def test_pull_request_not_kept_if_excluded(
        self, config, make_service, config_name: str, issue: ForgejoIssue
    ):
        config[SERVICE_NAME][config_name] = True
        config[SERVICE_NAME]["exclude_pull_requests"] = True
        assert not make_service(**config[SERVICE_NAME]).parsed_config.filter_issue(
            issue
        ), "pull request should not be kept when excluded"

    @pytest.mark.parametrize(
        "issue",
        [
            ASSIGNED_ISSUE,
            ASSIGNED_PULL_REQUEST,
            CREATED_ISSUE,
            CREATED_PULL_REQUEST,
            MENTIONED_ISSUE,
            MENTIONED_PULL_REQUEST,
            MENTIONED_IN_REVIEW_PULL_REQUEST,
            # TODO: not sure if this counts to Forgejo
            # USER_REPO_ISSUE,
            # USER_REPO_PULL_REQUEST,
            REVIEW_REQUESTED_PULL_REQUEST,
            REVIEW_REQUESTED_TEAM_PULL_REQUEST,
            REVIEWED_PULL_REQUEST,
        ],
    )
    def test_issue_kept_if_involved(self, config, make_service, issue: ForgejoIssue):
        config[SERVICE_NAME]["filter_pull_requests"] = True
        config = make_service(**config[SERVICE_NAME]).parsed_config

        config.include_involved_issues = False
        assert not config.filter_issue(issue), (
            "issue should not be kept when not keeping involved issues"
        )
        config.include_involved_issues = True
        assert config.filter_issue(issue), "involved issue should be kept when enabled"

    @pytest.mark.parametrize(
        "config_flag",
        [
            "include_assigned_issues",
            "include_created_issues",
            "include_mentioned_issues",
            "include_user_repos",
            "include_review_requested_issues",
            "include_reviewed_issues",
            "include_involved_issues",
        ],
    )
    def test_unrelated_issue_is_not_kept(self, config, make_service, config_flag: str):
        config[SERVICE_NAME][config_flag] = True
        assert not make_service(**config[SERVICE_NAME]).parsed_config.filter_issue(
            UNRELATED_PROCESSED_ISSUE
        ), "unrelated issue should not be kept"

    @pytest.mark.parametrize(
        "issue",
        [
            ASSIGNED_ISSUE,
            ASSIGNED_PULL_REQUEST,
            CREATED_ISSUE,
            CREATED_PULL_REQUEST,
            MENTIONED_ISSUE,
            MENTIONED_PULL_REQUEST,
            MENTIONED_IN_REVIEW_PULL_REQUEST,
            USER_REPO_ISSUE,
            USER_REPO_PULL_REQUEST,
            REVIEW_REQUESTED_PULL_REQUEST,
            REVIEW_REQUESTED_TEAM_PULL_REQUEST,
            REVIEWED_PULL_REQUEST,
            UNRELATED_ISSUE,
            UNRELATED_PULL_REQUEST,
        ],
    )
    def test_included_if_in_issue_urls(
        self, config, make_service, issue: ForgejoProcessedIssue
    ):
        config[SERVICE_NAME]["include_assigned_issues"] = False
        config[SERVICE_NAME]["include_created_issues"] = False
        config[SERVICE_NAME]["include_mentioned_issues"] = False
        config[SERVICE_NAME]["include_user_repos"] = False
        config[SERVICE_NAME]["include_review_requested_issues"] = False
        config[SERVICE_NAME]["include_reviewed_issues"] = False
        config[SERVICE_NAME]["include_involved_issues"] = False
        # issue_urls takes priority over exclude_pull_requests
        config[SERVICE_NAME]["exclude_pull_requests"] = True
        config[SERVICE_NAME]["issue_urls"] = issue.api_url
        assert make_service(**config[SERVICE_NAME]).parsed_config.filter_issue(issue), (
            "should keep issue by api url"
        )
        config[SERVICE_NAME]["issue_urls"] = issue.html_url
        assert make_service(**config[SERVICE_NAME]).parsed_config.filter_issue(issue), (
            "should keep issue by html url"
        )

    @pytest.mark.parametrize(
        "issue",
        [
            ASSIGNED_ISSUE,
            ASSIGNED_PULL_REQUEST,
            CREATED_ISSUE,
            CREATED_PULL_REQUEST,
            MENTIONED_ISSUE,
            MENTIONED_PULL_REQUEST,
            MENTIONED_IN_REVIEW_PULL_REQUEST,
            USER_REPO_ISSUE,
            USER_REPO_PULL_REQUEST,
            REVIEW_REQUESTED_PULL_REQUEST,
            REVIEW_REQUESTED_TEAM_PULL_REQUEST,
            REVIEWED_PULL_REQUEST,
            UNRELATED_ISSUE,
            UNRELATED_PULL_REQUEST,
        ],
    )
    def test_included_if_in_include_repos(
        self, config, make_service, issue: ForgejoProcessedIssue
    ):
        config[SERVICE_NAME]["include_assigned_issues"] = False
        config[SERVICE_NAME]["include_created_issues"] = False
        config[SERVICE_NAME]["include_mentioned_issues"] = False
        config[SERVICE_NAME]["include_user_repos"] = False
        config[SERVICE_NAME]["include_review_requested_issues"] = False
        config[SERVICE_NAME]["include_reviewed_issues"] = False
        config[SERVICE_NAME]["include_involved_issues"] = False
        config[SERVICE_NAME]["filter_pull_requests"] = True
        config[SERVICE_NAME]["include_repos"] = issue.repository.full_name
        assert make_service(**config[SERVICE_NAME]).parsed_config.filter_issue(issue), (
            "issue should be kept when repo is included"
        )

    @pytest.mark.parametrize(
        "issue",
        [
            ASSIGNED_PULL_REQUEST,
            CREATED_PULL_REQUEST,
            MENTIONED_PULL_REQUEST,
            MENTIONED_IN_REVIEW_PULL_REQUEST,
            USER_REPO_PULL_REQUEST,
            REVIEW_REQUESTED_PULL_REQUEST,
            REVIEW_REQUESTED_TEAM_PULL_REQUEST,
            REVIEWED_PULL_REQUEST,
            UNRELATED_PULL_REQUEST,
        ],
    )
    def test_exclude_pull_requests_from_include_repos(
        self, config, make_service, issue: ForgejoProcessedIssue
    ):
        config[SERVICE_NAME]["include_assigned_issues"] = True
        config[SERVICE_NAME]["include_created_issues"] = True
        config[SERVICE_NAME]["include_mentioned_issues"] = True
        config[SERVICE_NAME]["include_user_repos"] = True
        config[SERVICE_NAME]["include_review_requested_issues"] = True
        config[SERVICE_NAME]["include_reviewed_issues"] = True
        config[SERVICE_NAME]["include_involved_issues"] = True
        config[SERVICE_NAME]["exclude_pull_requests"] = True
        config[SERVICE_NAME]["include_repos"] = issue.repository.full_name
        assert not make_service(**config[SERVICE_NAME]).parsed_config.filter_issue(
            issue
        ), "pull request should be excluded even when repo is included"

    @pytest.mark.parametrize(
        "issue",
        [
            ASSIGNED_PULL_REQUEST,
            CREATED_PULL_REQUEST,
            MENTIONED_PULL_REQUEST,
            MENTIONED_IN_REVIEW_PULL_REQUEST,
            USER_REPO_PULL_REQUEST,
            REVIEW_REQUESTED_PULL_REQUEST,
            REVIEW_REQUESTED_TEAM_PULL_REQUEST,
            REVIEWED_PULL_REQUEST,
            UNRELATED_PULL_REQUEST,
        ],
    )
    def test_exclude_repos_overrides_category_includes(
        self, config, make_service, issue: ForgejoProcessedIssue
    ):
        config[SERVICE_NAME]["include_assigned_issues"] = True
        config[SERVICE_NAME]["include_created_issues"] = True
        config[SERVICE_NAME]["include_mentioned_issues"] = True
        config[SERVICE_NAME]["include_user_repos"] = True
        config[SERVICE_NAME]["include_review_requested_issues"] = True
        config[SERVICE_NAME]["include_reviewed_issues"] = True
        config[SERVICE_NAME]["include_involved_issues"] = True
        config[SERVICE_NAME]["exclude_repos"] = issue.repository.full_name
        assert not make_service(**config[SERVICE_NAME]).parsed_config.filter_issue(
            issue
        ), "issue should be excluded when repo is excluded"

    @pytest.mark.parametrize(
        "issue",
        [
            ASSIGNED_PULL_REQUEST,
            CREATED_PULL_REQUEST,
            MENTIONED_PULL_REQUEST,
            MENTIONED_IN_REVIEW_PULL_REQUEST,
            USER_REPO_PULL_REQUEST,
            REVIEW_REQUESTED_PULL_REQUEST,
            REVIEW_REQUESTED_TEAM_PULL_REQUEST,
            REVIEWED_PULL_REQUEST,
            UNRELATED_PULL_REQUEST,
        ],
    )
    def test_issue_urls_overrides_exclude_repos(
        self, config, make_service, issue: ForgejoProcessedIssue
    ):
        config[SERVICE_NAME]["include_assigned_issues"] = True
        config[SERVICE_NAME]["include_created_issues"] = True
        config[SERVICE_NAME]["include_mentioned_issues"] = True
        config[SERVICE_NAME]["include_user_repos"] = True
        config[SERVICE_NAME]["include_review_requested_issues"] = True
        config[SERVICE_NAME]["include_reviewed_issues"] = True
        config[SERVICE_NAME]["include_involved_issues"] = True
        config[SERVICE_NAME]["exclude_repos"] = issue.repository.full_name
        config[SERVICE_NAME]["issue_urls"] = issue.api_url

        assert make_service(**config[SERVICE_NAME]).parsed_config.filter_issue(issue), (
            "issue should be included by url even when repo is excluded"
        )


class TestForgejoClient:
    @responses.activate
    def test_get_repos(self):
        username = "a_user"
        repo_1 = LOGIN_USER_REPO

        repo_2 = LOGIN_USER_REPO
        repo_2.name += "_foo"
        repo_2.full_name += "_foo"

        responses.get(
            url=f"https://forgejo.internal/api/v1/users/{username}/repos",
            json=[repo_1.model_dump(mode="json")],
            headers={
                "link": f'<https://forgejo.internal/api/v1/users/{username}/repos?page=2>; rel="next"',
                "x-total-count": "2",
            },
        )
        responses.get(
            url=f"https://forgejo.internal/api/v1/users/{username}/repos?page=2",
            json=[repo_2.model_dump(mode="json")],
            headers={
                "link": f'<https://forgejo.internal/api/v1/users/{username}/repos?page=1>; rel="first"',
                "x-total-count": "2",
            },
        )

        client = ForgejoClient(host="https://forgejo.internal", token="token")
        fetched_repos = client.get_repos(username)
        assert fetched_repos == [repo_1, repo_2], "all repos should have been fetched"

    @responses.activate
    def test_get_query(self):
        q = "somequery"
        issue_1 = ASSIGNED_ISSUE
        pr_1 = CREATED_PULL_ISSUE
        issue_2 = MENTIONED_ISSUE
        pr_2 = USER_REPO_PULL_ISSUE

        responses.get(
            url=f"https://forgejo.internal/api/v1/search/issues?q={q}",
            json=[
                issue_1.model_dump(mode="json"),
                pr_1.model_dump(mode="json"),
                issue_2.model_dump(mode="json"),
            ],
            headers={
                "link": f'<https://forgejo.internal/api/v1/search/issues?query={q}&page=2>; rel="next"',
                "x-total-count": "4",
            },
        )
        responses.get(
            url=f"https://forgejo.internal/api/v1/search/issues?query={q}&page=2",
            json=[pr_2.model_dump(mode="json")],
            headers={
                "link": f'<https://forgejo.internal/api/v1/search/issues?query={q}&page=1>; rel="first"',
                "x-total-count": "4",
            },
        )

        client = ForgejoClient(host="https://forgejo.internal", token="token")
        fetched_issues = client.get_query(q)
        assert fetched_issues == [issue_1, pr_1, issue_2, pr_2], (
            "all issues should have been fetched"
        )

    def test_get_issues_for_repo(self):
        pass

    def test_get_issues_by_query(self):
        pass

    def test_get_comments(self):
        pass

    def test_get_pulls(self):
        pass


class TestForgejoIssueImpl:
    def test_to_taskwarrior(self):
        pass


class TestForgejoService:
    @pytest.mark.parametrize("login", ["tintin", "user"])
    @pytest.mark.parametrize(
        "host", ["https://codeberg.org", "https://forgejo.example.com"]
    )
    def test_get_keyring_service(self, login: str, host: str):
        # TODO: use make_service fixture
        config = SERVICE_CONFIG
        config["login"] = login
        config["host"] = host
        service = ForgejoService(**config, target="myservice")
        assert service.keyring_service == f"forgejo://{login}@{host}", (
            "keyring service mismatch"
        )

    def test_get_service_metadata(self):
        pass

    def test_get_owned_repo_issues(self):
        pass

    def test_get_query(self):
        pass

    def test_get_issues_by_query(self):
        pass

    def test_get_annotations(self):
        pass

    def test_get_pull_requests(self):
        pass

    def test_get_owner(self):
        pass

    def test_filter_issues(self):
        pass

    def test_filter_repos(self):
        pass

    def test_filter_repo_name(self):
        pass

    def test_include_issue(self):
        pass

    def test_issue_from_url(self):
        pass

    def test_get_issues(self):
        pass

    def test_issues(self):
        pass
