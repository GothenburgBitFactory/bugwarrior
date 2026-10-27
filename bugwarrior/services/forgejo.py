"""Bugwarrior service support class for Forgejo

Available classes:
- ForgejoClient(Service): Constructs Forgejo API strings
- ForgejoIssue(Issue): TaskWarrior Interface
- ForgejoService(Issue): Engine for firing off requests

Todo:
    * Add Basic and Bearer auth support
    * Flesh out more features offered by forgejo api
    * Use get_processed_url
    * Specify page size in pagination
"""

# Design:
# - Auth is generally separate from issue fetching
# - Can fetch issues for multiple owners/groups in one config
# - Custom query allowed
# - Labels as tags
# - Filter issues/PRs by assigned/creator/mention/etc.
# - Include all issues created by user
# - Include all PRs created by user
# - Include/exclude all PRs
# - Prefix project name with owner/group name

from collections.abc import Generator
from datetime import datetime
from enum import StrEnum
from locale import str as locale_str
import logging
import re
from typing import Any, NamedTuple, Self
from urllib.parse import urlsplit

from pydantic import BaseModel, Field, field_validator, model_validator
import requests
from requests.compat import str
import typing_extensions

from bugwarrior import config
from bugwarrior.services import Client, Issue, Service

log = logging.getLogger(__name__)  # pylint: disable-msg=C0103

# $ curl https://forgejo.example.org/api/v1/settings/api
# {
#   "max_response_items": 50,
#   "default_paging_num": 30,
#   "default_git_trees_per_page": 1000,
#   "default_max_blob_size": 10485760
# }


class RepoName(NamedTuple):
    owner: str
    name: str

    @staticmethod
    def from_tag(tag: str) -> "RepoName":
        return RepoName(*tag.split("/"))

    def __str__(self) -> str:
        return f"{self.owner}/{self.name}"


class ForgejoUser(BaseModel):
    """A user as represented by the Forgejo API."""

    id: int
    """The internal id number of the user."""

    login: str
    """The login username of the user."""


class ForgejoOrganization(BaseModel):
    id: int
    name: str
    full_name: str
    username: str
    email: str


class ForgejoTeamPermission(StrEnum):
    none = "none"
    read = "read"
    write = "write"
    admin = "admin"
    owner = "owner"


class ForgejoTeam(BaseModel):
    id: int
    description: str
    includes_all_repositories: bool = False
    name: str
    organization: ForgejoOrganization
    permission: ForgejoTeamPermission
    units: list[str] = Field(default_factory=list)
    units_map: dict[str, ForgejoTeamPermission] = Field(default_factory=dict)


class ForgejoRepository(BaseModel):
    """
    A repository as represented by the Forgejo API.

    The fields on this class are not complete and only represent those useful to bugwarrior.
    """

    has_issues: bool
    """Whether the repo has issues enabled."""
    has_pull_requests: bool
    """Whether the repo has pull requests enabled."""
    has_projects: bool
    """Whether the repo has projects enabled."""
    id: int
    """The internal id number of the repo."""
    name: str
    """
    The name of the repo, i.e. the "bar" in "foo/bar".
    """
    full_name: str
    """The full name of the repo, including the owner, e.g. "foo/bar"."""
    open_issues_count: int
    """The number of open issues."""
    open_pr_counter: int
    """The number of open pull requests."""
    owner: ForgejoUser
    """The user that owns this repo."""
    private: bool
    """Whether this repo is marked private."""
    topics: list[str]
    """The list of topics that this repo is tagged with."""


class ForgejoLabel(BaseModel):
    """A label as represented by the Forgejo API."""

    id: int
    """The internal id of the label."""
    name: str
    """The user-facing name of the label."""


class ForgejoPullRequestMeta(BaseModel):
    """Extra metadata on a ``ForgejoIssueReal`` if it represents a pull request."""

    draft: bool
    """Whether the pull request is in draft."""
    merged: bool
    """Whether the pull request has been merged."""
    merged_at: datetime | None = None
    """The timestamp of when the pull request was merged, if it has been merged."""


class ForgejoRepositoryMeta(BaseModel):
    """Metadata of the associated repository for a ``ForgejoIssueReal``."""

    full_name: str
    """The full name of the repository, e.g. "foo/bar"."""
    id: int
    """The internal id of the repository."""
    name: str
    """The name of the repository, i.e. the "bar" in "foo/bar"."""
    owner: str
    """The owner of the repository, i.e. the "foo" in "foo/bar"."""


class ForgejoIssueState(StrEnum):
    """The possible states an issue can be in."""

    All = "all"
    """Used in queries to indicate that issues of any state should be returned."""
    Closed = "closed"
    """The issue is closed."""
    Open = "open"
    """The issue is open."""


class ForgejoMilestone(BaseModel):
    closed_at: datetime | None = None
    closed_issues: int = 0
    created_at: datetime
    description: str
    due_on: datetime | None = None
    id: int
    open_issues: int
    state: ForgejoIssueState
    title: str
    updated_at: datetime | None = None


class ForgejoIssue(BaseModel):
    """
    The representation of an issue in the Forgejo API

    Note that pull requests are also represented as issues, just with the extra ``pull_request``
    field added.
    """

    assignee: ForgejoUser | None
    """The primary user this issue is assigned to."""
    assignees: list[ForgejoUser] | None
    """All users this issue is assigned to."""
    body: str
    """The body of the initial issue post, not including any comments."""
    closed_at: datetime | None
    """The timestamp this issue was closed on, if it is closed."""
    comments: int
    created_at: datetime
    """The timestamp this issue was created."""
    due_date: datetime | None
    """The timestamp for when this issue must be resolved."""
    id: int
    """The internal id of the issue."""
    labels: list[ForgejoLabel]
    """All labels applied to this issue."""
    milestone: ForgejoMilestone | None
    number: int
    """The issue number, as displayed in the UI and issue URL."""
    original_author: str
    """TODO."""
    pull_request: ForgejoPullRequestMeta | None
    """Extra metadata about the pull request, if this represents a pull request."""
    repository: ForgejoRepositoryMeta
    """Extra metadata about the repository this issue belongs to."""
    state: ForgejoIssueState
    """The current state of the issue."""
    title: str
    """The title of the issue."""
    updated_at: datetime
    """The last time this issue was updated."""
    # TODO: is this when the title/body/tags were last updated? Last commit to a PR? Last comment?
    url: str
    """The API URL for this issue."""
    html_url: str
    """The URL for humans to view this issue."""
    user: ForgejoUser
    """The user that created this issue."""


class ForgejoPrBranchInfo(BaseModel):
    label: str
    ref: str
    repo: ForgejoRepository
    repo_id: int
    sha: str


class ForgejoIssueComment(BaseModel):
    id: int
    body: str
    created_at: datetime
    html_url: str
    issue_url: str
    pull_request_url: str | None
    updated_at: datetime
    user: ForgejoUser


class ForgejoPrReviewComment(BaseModel):
    id: int
    body: str
    commit_id: str
    created_at: datetime
    diff_hunk: str
    extra_lines_count: int
    html_url: str
    original_commit_id: str
    original_position: int
    path: str
    position: int
    pull_request_review_id: int
    pull_request_url: str
    resolver: ForgejoUser | None
    updated_at: datetime
    user: ForgejoUser


# See https://codeberg.org/forgejo/forgejo/src/branch/forgejo/modules/structs/pull_review.go
class ForgejoPrReviewState(StrEnum):
    approved = "APPROVED"
    pending = "PENDING"
    comment = "COMMENT"
    request_changes = "REQUEST_CHANGES"
    request_review = "REQUEST_REVIEW"


class ForgejoPrReview(BaseModel):
    id: int
    body: str
    comments_count: int
    commit_id: str
    dismissed: bool
    html_url: str
    official: bool
    pull_request_url: str
    stale: bool
    state: ForgejoPrReviewState
    submitted_at: datetime
    team: ForgejoTeam | None
    updated_at: datetime
    user: ForgejoUser


class ForgejoPullRequest(BaseModel):
    id: int
    url: str
    number: int
    user: ForgejoUser
    title: str
    body: str
    labels: list[ForgejoLabel]
    assignee: ForgejoUser | None = None
    assignees: list[ForgejoUser] | None = None
    requested_reviewers: list[ForgejoUser]
    requested_reviewers_teams: list[ForgejoTeam]
    state: ForgejoIssueState
    draft: bool
    comments: int
    review_comments: int
    html_url: str
    mergeable: bool
    merged: bool
    merged_at: datetime | None = None
    base: ForgejoPrBranchInfo
    head: ForgejoPrBranchInfo


class ForgejoProcessedIssue(BaseModel):
    id: int
    number: int
    assignees: list[ForgejoUser] | None = None
    body: str
    closed_at: datetime | None = None
    created_at: datetime
    due_date: datetime | None = None
    labels: list[ForgejoLabel]
    milestone: ForgejoMilestone | None = None
    repository: ForgejoRepositoryMeta
    state: ForgejoIssueState
    title: str
    updated_at: datetime | None
    api_url: str
    html_url: str
    user: ForgejoUser
    comments: list[ForgejoIssueComment]
    is_pull_request: bool
    is_draft_pr: bool
    pr_review_comments: list[ForgejoPrReviewComment] | None
    pr_base_branch: ForgejoPrBranchInfo | None
    pr_merged_at: datetime | None
    pr_is_mergeable: bool | None
    pr_requested_reviewers: list[ForgejoUser]
    pr_requested_reviewers_teams: list[ForgejoTeam]

    @staticmethod
    def from_issue(
        issue: ForgejoIssue, comments: list[ForgejoIssueComment] | None
    ) -> "ForgejoProcessedIssue":
        return ForgejoProcessedIssue(
            id=issue.id,
            number=issue.number,
            assignees=issue.assignees,
            body=issue.body,
            closed_at=issue.closed_at,
            created_at=issue.created_at,
            due_date=issue.due_date,
            labels=issue.labels,
            milestone=issue.milestone,
            repository=issue.repository,
            state=issue.state,
            title=issue.title,
            updated_at=issue.updated_at,
            api_url=issue.url,
            html_url=issue.html_url,
            user=issue.user,
            comments=comments or [],
            is_pull_request=False,
            is_draft_pr=False,
            pr_review_comments=None,
            pr_base_branch=None,
            pr_merged_at=None,
            pr_is_mergeable=None,
            pr_requested_reviewers=[],
            pr_requested_reviewers_teams=[],
        )

    @staticmethod
    def from_pull_request(
        issue: ForgejoIssue,
        pr: ForgejoPullRequest,
        comments: list[ForgejoIssueComment],
        review_comments: list[ForgejoPrReviewComment],
    ) -> "ForgejoProcessedIssue":
        return ForgejoProcessedIssue(
            id=issue.id,
            number=issue.number,
            assignees=issue.assignees,
            body=issue.body,
            closed_at=issue.closed_at,
            created_at=issue.created_at,
            due_date=issue.due_date,
            labels=issue.labels,
            milestone=issue.milestone,
            repository=issue.repository,
            state=issue.state,
            title=issue.title,
            updated_at=issue.updated_at,
            api_url=issue.url,
            html_url=issue.html_url,
            user=issue.user,
            comments=comments,
            is_pull_request=True,
            is_draft_pr=pr.draft,
            pr_review_comments=review_comments,
            pr_base_branch=pr.base,
            pr_merged_at=pr.merged_at,
            pr_is_mergeable=pr.mergeable,
            pr_requested_reviewers=pr.requested_reviewers,
            pr_requested_reviewers_teams=pr.requested_reviewers_teams,
        )

    @property
    def is_merged_pr(self) -> bool:
        return self.pr_merged_at is not None

    @property
    def type(self) -> str:
        return "pull_request" if self.is_pull_request else "issue"


INCOMPATIBLE_WITH_QUERY = [
    "include_user_repos",
    "include_assigned_issues",
    "include_created_issues",
    "include_mentioned_issues",
    "include_reviewed_issues",
    "include_review_requested_issues",
    "filter_pull_requests",
    "exclude_pull_requests",
]


class ForgejoConfig(config.ServiceConfig):
    """Configuration for forgejo services."""

    # Strictly required.
    service: typing_extensions.Literal["forgejo"]
    host: str
    """The scheme and hostname of the Forgejo instance, e.g. ``https://codeberg.org``."""
    token: str = Field(..., min_length=1)
    """
    The personal access token to use to login.

    Forgejo also supports Basic and Bearer auth, but this implementation does not at this time.
    """
    login: str = Field(..., min_length=1)
    """The username to login as."""

    # optional
    # which repos to include/exclude
    include_user_repos: bool = False
    """Whether to include all repositories belonging to the authenticated user."""
    include_repos: config.ConfigList = []
    """
    A list of repositories to include issues and/or pull requests from, in the form "owner/repo".
    """
    exclude_repos: config.ConfigList = []
    """A list of repositories to exclude when searching for issues, in the form "owner/repo"."""

    # which issues/pull requests to include/exclude
    issue_urls: config.ConfigList = []
    """URLs of specific issues to include."""
    include_involved_issues: bool = False
    """Include all issues involving the authenticated user in any way."""
    include_assigned_issues: bool = False
    """Whether to include all issues assigned to the authenticated user."""
    include_created_issues: bool = False
    """Whether to include all issues created by the authenticated user."""
    include_mentioned_issues: bool = False
    """Whether to include all issues in which the authenticated user is mentioned."""
    include_reviewed_issues: bool = False
    """Whether to include all pull requests previously reviewed by the authenticated user."""
    include_review_requested_issues: bool = False
    """
    Whether to include all pull requests in which review is requested from the authenticated user.
    """
    # TODO: What should this default be?
    filter_pull_requests: bool = False
    """
    Whether to apply filters to pull requests on included repos.

    If ``False``, all pull requests on included repos will be turned into tasks.
    """
    exclude_pull_requests: bool = False
    """Whether to exclude all pull requests."""
    query: str | None = None
    """
    A custom query to use for finding issues and pull requests.

    Overrides all issue and pull request boolean flags.
    """

    # other settings
    import_labels_as_tags: bool = True
    """Whether to import Forgejo labels as tags."""
    project_owner_prefix: bool = False
    """
    Whether to prefix the Taskwarrior project name with the repo owner.

    If ``True``, the project name for repo "foo/bar" will look like `foo.bar`.
    Otherwise, it will be just `bar`.
    """
    label_template: str = "{{label}}"
    """The template for transforming a label value into a tag."""
    # TODO: double check whether other logic always prefixes with `forgejo_`.

    issue_limit: int = 50
    """
    The maximum number of issues the API may get from the host
    """

    def get(self, key: str, default: Any = None, to_type: type | None = None) -> Any:
        """
        Get a configuration field with optional default and type conversion.

        ``to_type`` must be able to take the raw value in its constructor.
        """
        try:
            value = self.parsed_config_parser.get(
                self.service_target, self._get_key(key)
            )
            if to_type:
                return to_type(value)
            return value
        except Exception:
            return default

    @field_validator("host", mode="after")
    @classmethod
    def validate_host(cls, host: str) -> str:
        parsed = urlsplit(host)
        if parsed.scheme != "https":
            raise ValueError(f'{host} should use the "https" scheme')
        if not parsed.hostname:
            raise ValueError(f"{host} must contain a hostname")
        return host

    @model_validator(mode="after")
    def validate_include_exclude_repos(self) -> Self:
        include = set(self.include_repos)
        exclude = set(self.exclude_repos)
        in_both = include & exclude
        if in_both:
            raise ValueError(
                f"one or more repos appear in both include_repos and exclude_repos: {in_both}"
            )
        return self

    @model_validator(mode="after")
    def do_not_allow_other_config_if_query_is_set(self) -> Self:
        if self.query is None:
            return self

        incompatible = []
        for attr in INCOMPATIBLE_WITH_QUERY:
            if getattr(self, attr, False) is True:
                incompatible.append(attr)

        if incompatible:
            non_compat = ", ".join(incompatible)
            raise ValueError(
                f'The following configuration items are incompatible with "query": {non_compat}'
            )

        return self

    @model_validator(mode="after")
    def validate_issue_urls(self) -> Self:
        for url in self.issue_urls:
            if not url.startswith(self.host):
                raise ValueError(
                    f"issue url {url} is inconsistent with the configured host {self.host}"
                )
            parsed = urlsplit(url)
            split = parsed.path.split("/")
            if "/api/v1" in parsed.path:
                expected1 = ["", "api", "v1", "repos", None, None, "issues", None]
                expected2 = ["", "api", "v1", "repos", None, None, "pulls", None]
            else:
                expected1 = ["", None, None, "issues", None]
                expected2 = ["", None, None, "pulls", None]

            # TODO: remove debug printing
            print(split)
            print(expected1)
            print(expected2)
            error = ValueError(f"{url} is not a valid issue or pull request url")
            if len(split) not in (len(expected1), len(expected2)):
                raise error

            for segment, (first, second) in zip(split, zip(expected1, expected2)):
                print(f"{segment}, {first}, {second}")
                if first is None or second is None:
                    continue
                if segment not in (first, second):
                    raise error
        return self

    def filter_issue_dict(self, entry: tuple[str, ForgejoIssue]) -> bool:
        return self.filter_issue(entry[1])

    def filter_issue(self, issue: ForgejoIssue) -> bool:
        if self.query is not None:
            # Assume the query is correct
            return True

        if issue.url in self.issue_urls or issue.html_url in self.issue_urls:
            return True

        if self.exclude_pull_requests and issue.pull_request is not None:
            return False

        if not self.filter_pull_requests and issue.pull_request is not None:
            return True

        if issue.repository.full_name in self.exclude_repos:
            return False

        if issue.repository.full_name not in self.include_repos:
            return False

        if self.include_involved_issues:
            pass

        if self.include_involved_issues or self.include_assigned_issues:
            if issue.assignee is not None and issue.assignee.login == self.login:
                return True
            if issue.assignees is not None and self.login in (
                u.login for u in issue.assignees
            ):
                return True

        if (
            self.include_involved_issues or self.include_created_issues
        ) and issue.user.login == self.login:
            return True

        if self.include_involved_issues or self.include_mentioned_issues:
            # TODO: how best to determine if user is mentioned?
            pass

        if (
            (self.include_involved_issues or self.include_review_requested_issues)
            and issue.pull_request is not None
            and issue.pull_request
        ):
            # TODO: is this the same as assignee?
            pass

        return self.include_user_repos and issue.repository.owner == self.login


class ForgejoClient(Client):
    """Builds Forgejo API strings
    Args:
        host (str): remote forgejo server
        auth (dict): authentication credentials

    Attributes:
        host (str): remote forgejo server
        auth (dict): authentication credentials
        session (requests.Session): requests persist settings

    Publics Functions:
    - get_repos:
    - get_query:
    - get_issues:
    - get_special_issues:
    - get_comments:
    - get_pulls:
    """

    def __init__(self, host: str, token: str) -> None:
        self.host = host
        self.token = token
        self.session = requests.Session()
        if self.token is not None:
            authorization = "token " + self.token
            self.session.headers["Authorization"] = authorization

    def _api_url(self, path: str, **context: Any) -> str:
        """Build the full url to the API endpoint"""
        baseurl: str = f"{self.host}/api/v1"
        return baseurl + path.format(**context)

    def get_repos(self, username: str) -> list[ForgejoRepository]:
        return self._get_all_paginated(
            self._api_url("/users/{username}/repos", username=username),
            ForgejoRepository,
        )

    def get_query(self, query: str) -> list[ForgejoIssue]:
        """Run a generic issue/PR query"""
        # https://codeberg.org/api/swagger#/issue/issueSearchIssues
        url = self._api_url("/search/issues?q={query}", query=query)
        return self._get_all_paginated(url, ForgejoIssue)

    def get_issues_for_repo(self, repo: RepoName) -> list[ForgejoIssue]:
        url = self._api_url(
            "/repos/{username}/{repo}/issues", username=repo.owner, repo=repo.name
        )
        return self._get_all_paginated(url, ForgejoIssue)

    def get_issues_by_query(self, query: str) -> list[ForgejoIssue]:
        """Returns all issues assigned to authenticated user given a specific query.

        This will return all issues this authenticated user has access to and then
        filter the issues with the query that the user supplied.
        """
        # https://codeberg.org/api/swagger#/issue/issueSearchIssues
        logging.info("Querying /repos/issues/search with query: " + query)
        url = self._api_url("/repos/issues/search?{query}", query=query)
        return self._get_all_paginated(url, ForgejoIssue)

    # TODO close to forgejo format: /comments/{id}
    def get_comments(self, repo: RepoName, number: int) -> list[ForgejoIssueComment]:
        url = self._api_url(
            "/repos/{username}/{repo}/issues/{number}/comments",
            username=repo.owner,
            repo=repo.name,
            number=number,
        )
        return self._get_all_paginated(url, ForgejoIssueComment)

    def get_pulls(self, repo: RepoName) -> list[ForgejoPullRequest]:
        url = self._api_url(
            "/repos/{username}/{repo}/pulls", username=repo.owner, repo=repo.name
        )
        return self._get_all_paginated(url, ForgejoPullRequest)

    def _get_all_paginated(
        self, url: str, type: type, subkey: str | None = None
    ) -> list[Any]:
        """Pagination utility.  Obnoxious."""

        kwargs = {}

        results = []
        link = {"next": url}
        total_expected = 0

        while "next" in link:
            response = self.session.get(link["next"], **kwargs)

            # Warn about the mis-leading 404 error code.  See:
            # https://forgejo.com/ralphbean/bugwarrior/issues/374
            # TODO this is a copy paste from github.py, see what forgejo produces
            if response.status_code == 404 and self.token is not None:
                log.warning(
                    "A '404' from forgejo may indicate an auth "
                    "failure. Make sure both that your token is correct "
                    "and that it has 'public_repo' and not 'public "
                    "access' rights."
                )

            json_res: list[Any] = self.json_response(response)

            if subkey is not None:
                json_res = [obj[subkey] for obj in json_res]

            results += (type(**x) for x in json_res)

            if total_expected < 1 and "x-total-count" in response.headers:
                total_expected = int(response.headers.get("x-total-count", "0"))

            link = self._link_field_to_dict(response.headers.get("link", None))

        return results

    # TODO: just copied from github.py
    @staticmethod
    def _link_field_to_dict(field: str | None) -> dict[str, str]:
        """Utility for ripping apart forgejo's Link header field.
        It's kind of ugly.

        Example headers (gotten using limit=7):
        x-total-count: 16
        link: <https://codeberg.org/api/v1/users/USER/repos?limit=7&page=2>; rel="next",<https://codeberg.org/api/v1/users/USER/repos?limit=7&page=3>; rel="last"

        Possible keys are first, prev, next, last
        """

        if not field:
            return {}

        return {
            part.split("; ")[1][5:-1]: part.split("; ")[0][1:-1]
                for part in field.split(", ")
        }


class ForgejoIssueImpl(Issue):
    TITLE = "forgejotitle"
    BODY = "forgejobody"
    DRAFT = "forgejodraft"
    CREATED_AT = "forgejocreatedon"
    UPDATED_AT = "forgejoupdatedat"
    CLOSED_AT = "forgejoclosedon"
    MILESTONE = "forgejomilestone"
    URL = "forgejourl"
    REPO = "forgejorepo"
    TYPE = "forgejotype"
    NUMBER = "forgejonumber"
    USER = "forgejouser"
    NAMESPACE = "forgejonamespace"
    STATE = "forgejostate"

    UNIQUE_KEY = (URL, TYPE)
    UDAS = {
        TITLE: {"type": "string", "label": "Forgejo Title"},
        BODY: {"type": "string", "label": "Forgejo Body"},
        DRAFT: {"type": "numeric", "label": "Forgejo Draft"},
        CREATED_AT: {"type": "date", "label": "Forgejo Created"},
        UPDATED_AT: {"type": "date", "label": "Forgejo Updated"},
        CLOSED_AT: {"type": "date", "label": "Forgejo Closed"},
        MILESTONE: {"type": "string", "label": "Forgejo Milestone"},
        REPO: {"type": "string", "label": "Forgejo Repo Slug"},
        URL: {"type": "string", "label": "Forgejo URL"},
        TYPE: {"type": "string", "label": "Forgejo Type"},
        NUMBER: {"type": "numeric", "label": "Forgejo Issue/PR #"},
        USER: {"type": "string", "label": "Forgejo User"},
        NAMESPACE: {"type": "string", "label": "Forgejo Namespace"},
        STATE: {"type": "string", "label": "Forgejo State"},
    }

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.parsed = ForgejoProcessedIssue(**self.record)

    @staticmethod
    def _normalize_label_to_tag(label: str) -> str:
        return re.sub(r"[^a-zA-Z0-9]", "_", label)

    def get_tags(self) -> list[str]:
        labels = [label.name for label in self.parsed.labels]
        return self.get_tags_from_labels(labels)

    def to_taskwarrior(self) -> dict:
        milestone = self.parsed.milestone
        if milestone is not None:
            milestone = milestone.title

        body = self.parsed.body
        if body:
            body = body.replace("\r\n", "\n").strip()

        if len(body) < 1:
            body = "No annotation was provided."

        created = self.parsed.created_at
        updated = self.parsed.updated_at
        closed = self.parsed.closed_at

        return {
            "project": self.extra["project"],
            "priority": self.config.default_priority,
            "annotations": self.extra.get("annotations", []),
            "tags": self.get_tags(),
            "entry": created,
            "end": closed,
            self.DRAFT: 1 if self.parsed.is_draft_pr else 0,
            self.URL: self.parsed.html_url,
            self.REPO: self.parsed.repository.full_name,
            self.TYPE: self.parsed.type,
            self.USER: self.parsed.user.login,
            self.TITLE: self.parsed.title,
            self.BODY: body,
            self.MILESTONE: milestone,
            self.NUMBER: self.parsed.number,
            self.CREATED_AT: created,
            self.UPDATED_AT: updated,
            self.CLOSED_AT: closed,
            self.NAMESPACE: self.parsed.repository.owner,  # self.extra['namespace'],
            self.STATE: self.parsed.state,
        }

    def get_default_description(self) -> str:
        return self.build_default_description(
            title=self.parsed.title,
            url=self.parsed.html_url,
            number=self.parsed.number,
            cls=self.parsed.type,
        )


class ForgejoService(Service):
    ISSUE_CLASS = ForgejoIssue
    CONFIG_SCHEMA = ForgejoConfig
    CONFIG_PREFIX = "forgejo"
    API_VERSION = 1

    def __init__(self, *args: Any, **kw: Any) -> None:
        super().__init__(*args, **kw)
        self.parsed_config = ForgejoConfig(**self.config.model_dump())

        token = self.get_secret("token", self.parsed_config.login)
        self.client = ForgejoClient(host=self.parsed_config.host, token=token)

        self.query = self.parsed_config.get(
            "query",
            default=f"involves:{self.parsed_config.login} state:open"
            if self.parsed_config.include_involved_issues
            else "",
            to_type=str,
        )

    @staticmethod
    def get_keyring_service(service_config: ForgejoConfig) -> str:
        username = service_config.login
        host = service_config.host
        return f"forgejo://{username}@{host}"

    def get_service_metadata(self) -> dict[str, Any]:
        return {
            "import_labels_as_tags": self.parsed_config.import_labels_as_tags,
            "label_template": self.parsed_config.label_template,
        }

    def get_owned_repo_issues(self, repo: RepoName) -> dict[str, ForgejoIssue]:
        """Grab all the issues"""
        return {issue.url: issue for issue in self.client.get_issues_for_repo(repo)}

    def get_query(self, query: str) -> dict[str, ForgejoIssue]:
        """Grab all issues matching a forgejo query"""
        return {issue.url: issue for issue in self.client.get_query(query)}

    def get_special_issues(self, query: str) -> dict[str, ForgejoIssue]:
        return {issue.url: issue for issue in self.client.get_issues_by_query(query)}

    @classmethod
    def get_repository_from_issue(
        cls, issue: ForgejoIssue | ForgejoPullRequest
    ) -> RepoName:
        parsed = urlsplit(issue.html_url)
        segments = parsed.path.split("/")
        # First segment is "" from the leading slash
        return RepoName(owner=segments[1], name=segments[2])

    def _comments(self, repo: RepoName, number: int) -> list[ForgejoIssueComment]:
        return self.client.get_comments(repo, number)

    def annotations(self, repo: RepoName, issue: ForgejoIssue) -> list[str]:
        url = issue.html_url
        annotations = []
        if self.parsed_config.annotation_comments:
            comments = self._comments(repo, issue.number)
            annotations = ((c.user.login, c.body) for c in comments)
        annotations_result = self.build_annotations(annotations, url)
        log.info(f"annotations: {annotations_result}")
        return annotations_result

    def _get_pull_requests(
        self, repo: RepoName
    ) -> list[tuple[RepoName, ForgejoPullRequest]]:
        """Grab all the pull requests"""
        return [(repo, i) for i in self.client.get_pulls(repo)]

    def get_owner(self, issue: tuple[RepoName, ForgejoIssue]) -> str:
        # TODO: verify
        if issue[1].assignee:
            return issue[1].assignee.login
        return issue[1].user.login

    def filter_issues(self, repo: ForgejoRepositoryMeta) -> bool:
        return self.filter_repo_name(repo.full_name)

    def filter_repos(self, repo: ForgejoRepository) -> bool:
        return self.filter_repo_name(repo.full_name)

    def filter_repo_name(self, full_name: str) -> bool:
        if self.parsed_config.exclude_repos and full_name in self.parsed_config.exclude_repos:
                return False

        if self.parsed_config.include_repos:
            return full_name in self.parsed_config.include_repos

        return True

    def include_issue(self, issue: ForgejoIssue) -> bool:
        if issue.pull_request is not None:
            if self.parsed_config.exclude_pull_requests:
                return False
            if not self.parsed_config.filter_pull_requests:
                return True
        return self.parsed_config.filter_issue(issue)

    def _get_json(self, url: str) -> Any:
        return self.client.json_response(self.client.session.get(url))

    def _get_json_obj(self, clazz: type, url: str) -> Any:
        return clazz(**self._get_json(url))

    def _get_json_list(self, clazz: type, url: str) -> list[Any]:
        return [clazz(**obj) for obj in self._get_json(url)]

    def _get_issue_comments(
        self, *, owner: str, repo: str, index: int
    ) -> list[ForgejoIssueComment]:
        json = self._get_json(
            f"{self.parsed_config.host}/api/v1/repos/{owner}/{repo}/pulls/{index}"
        )
        return [ForgejoIssueComment(**obj) for obj in json]

    def _get_pr(self, *, owner: str, repo: str, index: int) -> ForgejoPullRequest:
        return self._get_json_obj(
            ForgejoPullRequest,
            f"{self.parsed_config.host}/api/v1/repos/{owner}/{repo}/pulls/{index}",
        )

    def _get_reviews(
        self, *, owner: str, repo: str, index: int
    ) -> list[ForgejoPrReview]:
        return self._get_json_list(
            ForgejoPrReview,
            f"{self.parsed_config.host}/api/v1/repos/{owner}/{repo}/pulls/{index}/reviews",
        )

    def _get_review_comments(
        self, *, owner: str, repo: str, index: int, review_index: int
    ) -> list[ForgejoPrReviewComment]:
        url = f"{self.parsed_config.host}/api/v1/repos/{owner}/{repo}/pulls/{index}/reviews/{review_index}"
        return self._get_json_list(ForgejoPrReviewComment, url)

    def _issue_from_url(self, url: str) -> ForgejoIssue:
        # Allow users to provide the issue's API url
        # If they provide the user/HTML url, convert it to the API url
        if "/api/v1" not in url:
            path = url.removeprefix(self.parsed_config.host)
            assert not path.startswith("http")
            segments = iter(path.split("/"))
            owner = next(segments)
            if owner == "":
                owner = next(segments)
            name = next(segments)
            _ = next(segments)
            number = next(segments)
            url = (
                f"{self.parsed_config.host}/api/v1/repos/{owner}/{name}/issues/{number}"
            )

        return self._get_json_obj(ForgejoIssue, url)

    def _process_issue(self, issue: ForgejoIssue) -> ForgejoProcessedIssue:
        comments = self._get_issue_comments(
            owner=issue.repository.owner, repo=issue.repository.name, index=issue.id
        )

        if issue.pull_request is None:
            return ForgejoProcessedIssue.from_issue(issue, comments)

        pr = self._get_pr(
            owner=issue.repository.owner, repo=issue.repository.name, index=issue.id
        )
        review_comments = [
            comment
            for review in self._get_reviews(
                owner=issue.repository.owner, repo=issue.repository.name, index=issue.id
            )
            for comment in self._get_review_comments(
                owner=issue.repository.owner,
                repo=issue.repository.name,
                index=issue.id,
                review_index=review.id,
            )
        ]

        return ForgejoProcessedIssue.from_pull_request(
            issue, pr, comments, review_comments
        )

    def _get_issues(self) -> list[ForgejoIssue]:
        issues: dict[str, ForgejoIssue] = {}

        for url in self.parsed_config.issue_urls:
            issue = self._issue_from_url(url)
            issues[issue.url] = issue

        # query overrides all other options
        if self.query:
            issues.update(self.get_query(self.query))
            return list(issues.values())

        # Only query for all repos if an explicit
        # include_repos list is not specified.
        repos = []
        if self.parsed_config.include_repos:
            repos: list[str] = self.parsed_config.include_repos
        elif self.parsed_config.include_user_repos:
            all_repos = self.client.get_repos(self.parsed_config.login)
            repos = list(filter(self.filter_repos, all_repos))
            repos = [repo.full_name for repo in repos]

        for repo in repos:
            log.info(f"Found repo: {repo}")
            issues.update(self.get_owned_repo_issues(RepoName.from_tag(repo)))

        """
        A variable used to represent the attachable HTTP query that can be attached to the
        /repos/issues/search API end.

        if httpQuery is set to "review_requested=True?mentioned=True" for example, then the
        /repos/issues/search API end will be told to search for all issues where a review is
        requested AND where the user is mentioned.
        """
        httpQuery = "limit=" + locale_str(self.parsed_config.issue_limit) + "&"

        # TODO: seems like query uses implicit OR, so this could maybe all be combined into a single
        # query

        if self.parsed_config.include_assigned_issues:
            log.info("assigned was true")
            issues.update(
                filter(
                    self.parsed_config.filter_issue_dict,
                    self.get_special_issues(httpQuery + "assigned=true&").items(),
                )
            )
        if self.parsed_config.include_created_issues:
            log.info("created was true")
            issues.update(
                filter(
                    self.parsed_config.filter_issue_dict,
                    self.get_special_issues(httpQuery + "created=true&").items(),
                )
            )
        if self.parsed_config.include_mentioned_issues:
            log.info("mentioned was true")
            issues.update(
                filter(
                    self.parsed_config.filter_issue_dict,
                    self.get_special_issues(httpQuery + "mentioned=true&").items(),
                )
            )

        if self.parsed_config.include_review_requested_issues:
            log.info("review request was true")
            issues.update(
                filter(
                    self.parsed_config.filter_issue_dict,
                    self.get_special_issues(
                        httpQuery + "review_requested=true&"
                    ).items(),
                )
            )
        if self.parsed_config.include_reviewed_issues:
            log.info("review request was true")
            issues.update(
                filter(
                    self.parsed_config.filter_issue_dict,
                    self.get_special_issues(httpQuery + "reviewed=true&").items(),
                )
            )

        return list(issues.values())

    def issues(self) -> Generator[ForgejoIssue]:
        issues = self._get_issues()

        issues = [
            self._process_issue(issue) for issue in filter(self.include_issue, issues)
        ]

        for issue in issues:
            projectName = issue.repository.name

            issue_obj = self.get_issue_for_record(issue.model_dump())
            if self.parsed_config.project_owner_prefix:
                projectName = issue.repository.owner + "." + projectName
            extra = {
                "project": projectName,
                "type": "pull_request" if "pull_request" in issue else "issue",
                "annotations": ["#" + locale_str(issue.number) + " - " + issue.title],
                # TODO: user login or repo owner?
                "namespace": self.parsed_config.login,
            }
            issue_obj.extra.update(extra)
            yield issue_obj
