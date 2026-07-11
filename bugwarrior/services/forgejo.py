"""Bugwarrior service support class for Forgejo

Available classes:
- ForgejoClient(Service): Constructs Forgejo API strings
- ForgejoIssue(Issue): TaskWarrior Interface
- ForgejoService(Issue): Engine for firing off requests

Todo:
    * Add Basic and Bearer auth support
    * Flesh out more features offered by forgejo api
    * Use get_processed_url
"""
from builtins import filter
from enum import StrEnum
from locale import str as locale_str
import logging
import re
import sys
from typing import Any, Optional, Type, Generator

from pydantic import BaseModel
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


class ForgejoUser(BaseModel):
    id: int
    # username
    login: str


class ForgejoRepository(BaseModel):
    # The fields here are not complete and only represent those useful to bugwarrior
    has_issues: bool
    has_pull_requests: bool
    has_projects: bool
    id: int
    name: str
    full_name: str
    open_issues_count: int
    open_pr_counter: int
    owner: ForgejoUser
    private: bool
    topics: list[str]


class ForgejoLabel(BaseModel):
    id: int
    name: str


class ForgejoPullRequestMeta(BaseModel):
    draft: bool
    merged: bool
    # datetime
    merged_at: Optional[str] = None


class ForgejoRepositoryMeta(BaseModel):
    full_name: str
    id: int
    name: str
    owner: str


class ForgejoIssueState(StrEnum):
    All = "all"
    Closed = "closed"
    Open = "open"


class ForgejoIssueReal(BaseModel):
    assignee: Optional[ForgejoUser]
    assignees: Optional[list[ForgejoUser]]
    body: str
    closed_at: str  # datetime
    created_at: str  # datetime
    due_date: str  # datetime
    id: int
    labels: list[ForgejoLabel]
    # milestone: forgejomilestone
    number: int
    original_author: str
    pull_request: Optional[ForgejoPullRequestMeta]
    repository: ForgejoRepositoryMeta
    state: ForgejoIssueState
    title: str
    updated_at: str  # datetime
    url: str
    html_url: str
    user: ForgejoUser


class ForgejoPrBranchInfo(BaseModel):
    label: str
    ref: str
    repo: ForgejoRepository
    repo_id: int
    sha: str


class ForgejoComment(BaseModel):
    id: int
    body: str
    created_at: str
    html_url: str
    issue_url: str
    pull_request_url: str
    updated_at: str
    user: ForgejoUser


class ForgejoPullRequest(BaseModel):
    id: int
    url: str
    number: int
    user: ForgejoUser
    title: str
    body: str
    labels: list[ForgejoLabel]
    assignee: Optional[ForgejoUser]
    assignees: Optional[list[ForgejoUser]]
    requested_reviewers: list[ForgejoUser]
    requested_reviewers_teams: list[ForgejoUser]
    state: ForgejoIssueState
    draft: bool
    comments: int
    review_comments: int
    html_url: str
    mergeable: bool
    merged: bool
    merged_at: str
    base: ForgejoPrBranchInfo


# TODO: Document this with docstrings
class ForgejoConfig(config.ServiceConfig):
    # strictly required
    service: typing_extensions.Literal['forgejo']
    host: str
    # Forgejo supports Basic, Bearer, and Token auth
    # For now, we support only Token auth
    token: str
    login: str

    # optional
    include_assigned_issues: bool = False
    include_created_issues: bool = False
    include_mentioned_issues: bool = False
    include_review_requested_issues: bool = False
    import_labels_as_tags: bool = True
    involved_issues: bool = False
    project_owner_prefix: bool = False
    include_repos: config.ConfigList = []
    exclude_repos: config.ConfigList = []
    label_template: str = '{{label}}'
    filter_pull_requests: bool = False
    exclude_pull_requests: bool = False

    """
    The maximum number of issues the API may get from the host
    """
    issue_limit: int = 100

    def get(self, key: str, default: Any = None, to_type: Optional[Type] = None) -> Any:
        try:
            value = self.config_parser.get(self.service_target, self._get_key(key))
            if to_type:
                return to_type(value)
            return value
        except Exception:
            return default


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
            authorization = 'token ' + self.token
            self.session.headers['Authorization'] = authorization

    def _api_url(self, path: str, **context: Any) -> str:
        """Build the full url to the API endpoint"""
        baseurl: str = 'https://{host}/api/v1'.format(host=self.host)
        print(baseurl)
        print(path.format(**context))
        return baseurl + path.format(**context)

    # TODO Modify these for forgejo support
    def get_repos(self, username: str) -> list[ForgejoRepository]:
        # user_repos = self._getter(self._api_url("/user/repos?per_page=100"))
        public_repos = self._get_all_paginated(
            self._api_url('/users/{username}/repos', username=username),
            ForgejoRepository,
        )
        return public_repos

    def get_query(self, query: str) -> list[ForgejoIssueReal]:
        """Run a generic issue/PR query"""
        url = self._api_url('/search/issues?q={query}&per_page=100', query=query)
        return self._get_all_paginated(url, ForgejoIssueReal, subkey='items')

    def get_issues(self, username: str, repo: str) -> list[ForgejoIssueReal]:
        url = self._api_url(
            '/repos/{username}/{repo}/issues?per_page=100', username=username, repo=repo
        )
        return self._get_all_paginated(url, ForgejoIssueReal)

    def get_special_issues(self, username: str, query: str) -> list[ForgejoIssueReal]:
        """Returns all issues assigned to authenticated user given a specific query.

        This will return all issues this authenticated user has access to and then
        filter the issues with the query that the user supplied.
        """
        logging.info("Querying /repos/issues/search with query: " + query)
        url = self._api_url(
            '/repos/issues/search?{query}', username=username, query=query
        )
        return self._get_all_paginated(url, ForgejoIssueReal)

    # TODO close to forgejo format: /comments/{id}
    def get_comments(self, username: str, repo: str, number: int) -> list[ForgejoComment]:
        url = self._api_url(
            '/repos/{username}/{repo}/issues/{number}/comments?per_page=100',
            username=username,
            repo=repo,
            number=number,
        )
        return self._get_all_paginated(url, ForgejoComment)

    def get_pulls(self, username: str, repo: str) -> list[ForgejoPullRequest]:
        url = self._api_url(
            '/repos/{username}/{repo}/pulls?per_page=100', username=username, repo=repo
        )
        return self._get_all_paginated(url, ForgejoPullRequest)

    def _get_all_paginated(self, url: str, type: Type, subkey: Optional[str] = None) -> list[Any]:
        """Pagination utility.  Obnoxious."""

        kwargs = {}

        results = []
        link = dict(next=url)

        while 'next' in link:
            response = self.session.get(link['next'], **kwargs)

            # Warn about the mis-leading 404 error code.  See:
            # https://forgejo.com/ralphbean/bugwarrior/issues/374
            # TODO this is a copy paste from github.py, see what forgejo produces
            if response.status_code == 404 and self.token is not None:
                log.warning(
                    'A \'404\' from forgejo may indicate an auth '
                    'failure. Make sure both that your token is correct '
                    'and that it has \'public_repo\' and not \'public '
                    'access\' rights.'
                )

            json_res = self.json_response(response)

            if subkey is not None:
                json_res = json_res[subkey]

            results += map(lambda x: type(**x), json_res)

            link = self._link_field_to_dict(response.headers.get('link', None))

        return results

    # TODO: just copied from github.py
    @staticmethod
    def _link_field_to_dict(field: Optional[str]) -> dict[str, str]:
        """Utility for ripping apart forgejo's Link header field.
        It's kind of ugly.
        """

        if not field:
            return dict()

        return dict(
            [
                (part.split('; ')[1][5:-1], part.split('; ')[0][1:-1])
                for part in field.split(', ')
            ]
        )


class ForgejoIssue(Issue):
    TITLE = 'forgejotitle'
    BODY = 'forgejobody'
    DRAFT = 'forgejodraft'
    CREATED_AT = 'forgejocreatedon'
    UPDATED_AT = 'forgejoupdatedat'
    CLOSED_AT = 'forgejoclosedon'
    MILESTONE = 'forgejomilestone'
    URL = 'forgejourl'
    REPO = 'forgejorepo'
    TYPE = 'forgejotype'
    NUMBER = 'forgejonumber'
    USER = 'forgejouser'
    NAMESPACE = 'forgejonamespace'
    STATE = 'forgejostate'

    UNIQUE_KEY = (URL, TYPE)
    UDAS = {
        TITLE: {'type': 'string', 'label': 'Forgejo Title'},
        BODY: {'type': 'string', 'label': 'Forgejo Body'},
        DRAFT: {'type': 'numeric', 'label': 'Forgejo Draft'},
        CREATED_AT: {'type': 'date', 'label': 'Forgejo Created'},
        UPDATED_AT: {'type': 'date', 'label': 'Forgejo Updated'},
        CLOSED_AT: {'type': 'date', 'label': 'Forgejo Closed'},
        MILESTONE: {'type': 'string', 'label': 'Forgejo Milestone'},
        REPO: {'type': 'string', 'label': 'Forgejo Repo Slug'},
        URL: {'type': 'string', 'label': 'Forgejo URL'},
        TYPE: {'type': 'string', 'label': 'Forgejo Type'},
        NUMBER: {'type': 'numeric', 'label': 'Forgejo Issue/PR #'},
        USER: {'type': 'string', 'label': 'Forgejo User'},
        NAMESPACE: {'type': 'string', 'label': 'Forgejo Namespace'},
        STATE: {'type': 'string', 'label': 'Forgejo State'},
    }

    @staticmethod
    def _normalize_label_to_tag(label: str) -> str:
        return re.sub(r'[^a-zA-Z0-9]', '_', label)

    def get_tags(self) -> list[str]:
        labels = [label['name'] for label in self.record.get('labels', [])]
        return self.get_tags_from_labels(labels)

    def to_taskwarrior(self) -> dict:
        milestone = self.record['milestone']
        if milestone:
            milestone = milestone['title']

        body = self.record['body']
        if body:
            body = body.replace('\r\n', '\n')

        if len(body) < 1:
            body = "No annotation was provided."

        created = self.parse_date(self.record.get('created_at'))
        updated = self.parse_date(self.record.get('updated_at'))
        closed = self.parse_date(self.record.get('closed_at'))

        return {
            'project': self.extra['project'],
            'priority': self.config.default_priority,
            'annotations': self.extra.get('annotations', []),
            'tags': self.get_tags(),
            'entry': created,
            'end': closed,
            self.DRAFT: self.record.get('draft', 0),
            self.URL: self.record['html_url'],
            self.REPO: self.record['repository']['full_name'],
            self.TYPE: self.extra['type'],
            self.USER: self.record['user']['login'],
            self.TITLE: self.record['title'],
            self.BODY: body,
            self.MILESTONE: milestone,
            self.NUMBER: self.record['number'],
            self.CREATED_AT: created,
            self.UPDATED_AT: updated,
            self.CLOSED_AT: closed,
            self.NAMESPACE: self.record['repository'][
                'owner'
            ],  # self.extra['namespace'],
            self.STATE: self.record.get('state', ''),
        }

    def get_default_description(self) -> str:
        log.info('In get_default_description')
        return self.build_default_description(
            title=self.record['title'],
            url=self.record['html_url'],
            number=self.record['number'],
            cls=self.extra['type'],
        )


class ForgejoService(Service):
    ISSUE_CLASS = ForgejoIssue
    CONFIG_SCHEMA = ForgejoConfig
    CONFIG_PREFIX = 'forgejo'
    API_VERSION = 1

    def __init__(self, *args: Any, **kw: Any) -> None:
        super(ForgejoService, self).__init__(*args, **kw)

        print(self.config.token)
        token = self.config.token
        if token is None:
            # Probably should be called by validate_config
            logging.critical("ERROR! No token was provided in config!")
            sys.exit(1)

        token = self.get_secret("token", self.config.login)

        # TODO: document these with docstrings
        self.client = ForgejoClient(host=self.config.host, token=token)

        self.query = self.config.get(
            'query',
            default='involves:{user} state:open'.format(user=self.config.login)
            if self.config.involved_issues
            else '',
            to_type=str,
        )

    @staticmethod
    def get_keyring_service(service_config: ForgejoConfig) -> str:
        # TODO grok this
        username = service_config.login
        host = service_config.host
        return 'forgejo://{username}@{host}/{username}'.format(
            username=username, host=host
        )

    def get_service_metadata(self) -> dict[str, Any]:
        return {
            'import_labels_as_tags': self.config.import_labels_as_tags,
            'label_template': self.config.label_template,
        }

    def get_owned_repo_issues(self, tag: str) -> dict[str, tuple[str, ForgejoIssueReal]]:
        """Grab all the issues"""
        issues = {}
        for issue in self.client.get_issues(*tag.split('/')):
            issues[issue.url] = (tag, issue)
        return issues

    def get_query(self, query: str) -> dict[str, tuple[str, ForgejoIssueReal]]:
        """Grab all issues matching a forgejo query"""
        log.info('In get_query')
        issues = {}
        for issue in self.client.get_query(query):
            url = issue.url
            try:
                repo = self.get_repository_from_issue(issue)
            except ValueError as e:
                log.critical(e)
            else:
                issues[url] = (repo, issue)
        return issues

    def get_special_issues(self, username: str, query: str) -> dict[str, tuple[str, ForgejoIssueReal]]:
        issues = {}
        for issue in self.client.get_special_issues(username, query):
            repos = self.get_repository_from_issue(issue)
            issues[issue.url] = (repos, issue)
        return issues

    @classmethod
    def get_repository_from_issue(cls, issue: ForgejoIssueReal | ForgejoPullRequest) -> str:
        # TODO: this strips the last two segments from
        # https://codeberg.org/user/repo/issues/1 into
        # https://codeberg.org/user/repo
        #
        # We could also do something like `https://{host}/{issue.repository.full_name}`
        # but we don't necessarily know the scheme to use.
        return issue.html_url.rsplit("/", 2)[0]

    def _comments(self, tag: str, number: int) -> list[ForgejoComment]:
        user, repo = tag.split('/')
        return self.client.get_comments(user, repo, number)

    def annotations(self, full_name: str, issue: ForgejoIssueReal) -> list[str]:
        log.info('in Annotations')
        # log.info(repr(issue))
        log.info('body: {}'.format(issue.body))
        url = issue.html_url
        annotations = []
        if self.config.annotation_comments:
            comments = self._comments(full_name, issue.number)
            # log.info(" got comments for %s", issue.url)
            annotations = ((c.user.login, c.body) for c in comments)
        annotations_result = self.build_annotations(annotations, url)
        log.info('annotations: {}'.format(annotations_result))
        return annotations_result

    def _reqs(self, full_name: str) -> list[tuple[str, ForgejoPullRequest]]:
        """Grab all the pull requests"""
        return [(full_name, i) for i in self.client.get_pulls(*full_name.split('/'))]

    def get_owner(self, issue: tuple[str, ForgejoIssueReal]) -> str:
        if issue[1].assignee:
            return issue[1].assignee.login
        return issue[1].user.login

    def filter_issues(self, repo: ForgejoRepositoryMeta) -> bool:
        return self.filter_repo_name(repo.full_name)

    def filter_repos(self, repo: ForgejoRepository) -> bool:
        if repo.owner != self.config.login:
            return False

        return self.filter_repo_name(repo.full_name)

    def filter_repo_name(self, full_name: str) -> bool:
        if self.config.exclude_repos:
            if full_name in self.config.exclude_repos:
                return False

        if self.config.include_repos:
            if full_name in self.config.include_repos:
                return True
            else:
                return False

        return True

    def include(self, issue: tuple[str, ForgejoIssueReal]) -> bool:
        if issue[1].pull_request is not None:
            if self.config.exclude_pull_requests:
                return False
            if not self.config.filter_pull_requests:
                return True
        return super(ForgejoService, self).include(issue)

    def issues(self) -> Generator[ForgejoIssue]:
        issues = {}
        if self.query:
            issues.update(self.get_query(self.query))

        if self.config.get('include_user_repos', True, bool):
            # Only query for all repos if an explicit
            # include_repos list is not specified.
            if self.config.include_repos:
                repos: list[str] = self.config.include_repos
            else:
                all_repos = self.client.get_repos(self.config.login)
                repos = filter(self.filter_repos, all_repos)
                repos = [repo.name for repo in repos]

            for repo in repos:
                log.info('Found repo: {}'.format(repo))
                issues.update(self.get_owned_repo_issues(self.config.login + '/' + repo))

            '''
            A variable used to represent the attachable HTTP query that can be attached to the /repos/issues/search API end.

            if httpQuery is set to "review_requested=True?mentioned=True" for example, then the /repos/issues/search API end will be told to search for all issues where a review is requested AND where the user is mentioned.
            '''
            httpQuery = "limit=" + locale_str(self.config.issue_limit) + "&"

            if self.config.get('include_assigned_issues', True, bool):
                log.info("assigned was true")
                issues.update(
                    filter(
                        self.config.filter_issues,
                        self.get_special_issues(
                            self.config.login, httpQuery + "assigned=true&"
                        ).items(),
                    )
                )
            if self.config.get('include_created_issues', True, bool):
                log.info("created was true")
                issues.update(
                    filter(
                        self.config.filter_issues,
                        self.get_special_issues(
                            self.config.login, httpQuery + "created=true&"
                        ).items(),
                    )
                )
            if self.config.get('include_mentioned_issues', True, bool):
                log.info("mentioned was true")
                issues.update(
                    filter(
                        self.config.filter_issues,
                        self.get_special_issues(
                            self.config.login, httpQuery + "mentioned=true&"
                        ).items(),
                    )
                )
            if self.config.get('include_review_requested_issues', True, bool):
                log.info("review request was true")
                issues.update(
                    filter(
                        self.config.filter_issues,
                        self.get_special_issues(
                            self.config.login, httpQuery + "review_requested=true&"
                        ).items(),
                    )
                )

        log.info(' Found %i issues.', len(issues))  # these were debug logs
        issues = list(filter(self.include, issues.values()))
        log.info(' Pruned down to %i issues.', len(issues))  # these were debug logs

        for tag, issue in issues:
            # Stuff this value into the upstream dict for:
            # https://forgejo.com/ralphbean/bugwarrior/issues/159
            projectName = issue.repository.name

            issue_obj = self.get_issue_for_record(issue.model_dump())
            if self.config.project_owner_prefix:
                projectName = issue.repository.owner + '.' + projectName
            extra = {
                'project': projectName,
                'type': 'pull_request' if 'pull_request' in issue else 'issue',
                'annotations': [
                    "#" + locale_str(issue.number) + " - " + issue.title
                ],
                'namespace': self.config.login,
            }
            issue_obj.extra.update(extra)
            yield issue_obj
