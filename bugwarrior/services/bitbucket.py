import logging
from typing import Any, Iterator, Literal, Union

from pydantic import Field, model_validator
import requests

from bugwarrior import config
from bugwarrior.services import Client, Issue, Service
from bugwarrior.task import Task, Udas

log = logging.getLogger(__name__)


class BitbucketConfig(config.ServiceConfig):
    _DEPRECATE_FILTER_MERGE_REQUESTS = True
    filter_merge_requests: Union[bool, Literal['Undefined']] = 'Undefined'

    service: Literal['bitbucket']
    KEYRING_SERVICE = "bitbucket://{key}/{username}"

    username: str

    login: str = 'Undefined'
    password: str = 'Undefined'

    key: str
    secret: str

    include_repos: config.ConfigList = []
    exclude_repos: config.ConfigList = []
    include_merge_requests: Union[bool, Literal['Undefined']] = 'Undefined'
    project_owner_prefix: bool = False

    @model_validator(mode='after')
    def deprecate_password_authentication(self) -> "BitbucketConfig":
        if self.login != 'Undefined' or self.password != 'Undefined':
            log.warning(
                'Bitbucket has disabled password authentication and, as such, '
                'the "login" and "password" options are deprecated and should '
                'be removed from your configuration file.'
            )
        return self


class BitbucketUdas(Udas):
    """Service-specific UDAs contributed by Bitbucket."""

    UNIQUE_KEY = ('bitbucketurl',)

    bitbuckettitle: str = Field(title='Bitbucket Title')
    bitbucketurl: str = Field(title='Bitbucket URL')
    bitbucketid: int = Field(title='Bitbucket Issue ID')


class BitbucketTask(Task):
    udas: BitbucketUdas


class BitbucketIssue(Issue):
    PRIORITY_MAP = {
        'trivial': 'L',
        'minor': 'L',
        'major': 'M',
        'critical': 'H',
        'blocker': 'H',
    }

    def to_taskwarrior(self) -> BitbucketTask:
        return BitbucketTask(
            project=self.extra['project'],
            priority=self.get_priority(),
            annotations=self.extra['annotations'],
            udas=BitbucketUdas(
                bitbuckettitle=self.record['title'],
                bitbucketurl=self.extra['url'],
                bitbucketid=self.record['id'],
            ),
        )

    def get_default_description(self) -> str:
        return self.build_default_description(
            title=self.record['title'],
            url=self.extra['url'],
            number=self.record['id'],
            cls='issue',
        )


class BitbucketService(Service):
    API_VERSION = 2.0
    ISSUE_CLASS = BitbucketIssue
    TASK_SCHEMA = BitbucketTask
    CONFIG_SCHEMA = BitbucketConfig

    BASE_API2 = 'https://api.bitbucket.org/2.0'
    BASE_URL = 'https://bitbucket.org/'

    def __init__(
        self, config: BitbucketConfig, main_config: config.MainSectionConfig
    ) -> None:
        super().__init__(config, main_config)

        oauth = (self.config.key, self.get_secret('secret', self.config.key))
        refresh_token = self.main_config.data.get('bitbucket_refresh_token')

        if refresh_token:
            response = requests.post(
                self.BASE_URL + 'site/oauth2/access_token',
                data={'grant_type': 'refresh_token', 'refresh_token': refresh_token},
                auth=oauth,
            ).json()
        else:
            response = requests.post(
                self.BASE_URL + 'site/oauth2/access_token',
                data={'grant_type': 'client_credentials'},
                auth=oauth,
            ).json()

            self.main_config.data.set(
                'bitbucket_refresh_token', response['refresh_token']
            )

        self.requests_kwargs: dict[str, Any] = {
            'headers': {'Authorization': f"Bearer {response['access_token']}"}
        }

    def filter_repos(self, repo_tag: str) -> bool:
        repo = repo_tag.split('/').pop()

        if self.config.exclude_repos:
            if repo in self.config.exclude_repos:
                return False

        if self.config.include_repos:
            if repo in self.config.include_repos:
                return True
            else:
                return False

        return True

    def get_data(self, url: str) -> dict[str, Any]:
        """Perform a request to the fully qualified url and return json."""
        return Client.json_response(requests.get(url, **self.requests_kwargs))

    def get_collection(self, url: str) -> Iterator[Any]:
        """Pages through an object collection from the bitbucket API.
        Returns an iterator that lazily goes through all the 'values'
        of all the pages in the collection."""
        next_url: str | None = self.BASE_API2 + url
        while next_url is not None:
            response = self.get_data(next_url)
            yield from response['values']
            next_url = response.get('next', None)

    def fetch_issues(self, tag: str) -> list[tuple[str, dict[str, Any]]]:
        response = self.get_collection('/repositories/%s/issues/' % (tag))
        return [(tag, issue) for issue in response]

    def fetch_pull_requests(self, tag: str) -> list[tuple[str, dict[str, Any]]]:
        response = self.get_collection('/repositories/%s/pullrequests/' % tag)
        return [(tag, issue) for issue in response]

    def get_annotations(self, tag: str, issue: dict[str, Any], url: str) -> list[str]:
        response = self.get_collection(
            '/repositories/%s/pullrequests/%i/comments' % (tag, issue['id'])
        )
        return self.build_annotations(
            (
                (comment['user']['username'], comment['content']['raw'])
                for comment in response
            ),
            url,
        )

    def get_owner(self, issue: tuple[str, dict[str, Any]]) -> str | None:
        _, issue_dict = issue
        assignee = issue_dict.get('assignee', None)
        if assignee is not None:
            return assignee.get('username', None)
        return None

    def include(self, issue: tuple[str, dict[str, Any]]) -> bool:
        """Return true if the issue in question should be included"""
        if self.config.only_if_assigned:
            owner = self.get_owner(issue)
            include_owners: list[str | None] = [self.config.only_if_assigned]

            if self.config.also_unassigned:
                include_owners.append(None)

            return owner in include_owners

        return True

    def issues(self) -> Iterator[Task]:
        user = self.config.username
        response = self.get_collection('/repositories/' + user + '/')
        repo_tags = list(
            filter(
                self.filter_repos,
                [repo['full_name'] for repo in response if repo.get('has_issues')],
            )
        )

        issues = sum((self.fetch_issues(repo) for repo in repo_tags), [])
        log.debug(" Found %i total.", len(issues))

        closed = ['resolved', 'duplicate', 'wontfix', 'invalid', 'closed']
        try:
            issues = [tup for tup in issues if tup[1]['status'] not in closed]
        except KeyError:  # Undocumented API change.
            issues = [tup for tup in issues if tup[1]['state'] not in closed]
        issues = list(filter(self.include, issues))
        log.debug(" Pruned down to %i", len(issues))

        for tag, issue in issues:
            tagParts = tag.split('/')
            projectName = tagParts[1]
            if self.config.project_owner_prefix:
                projectName = tagParts[0] + "." + projectName
            url = issue['links']['html']['href']
            extras = {
                'project': projectName,
                'url': url,
                'annotations': self.get_annotations(tag, issue, url),
            }
            yield self.process_record(issue, extras)

        if self.config.include_merge_requests:
            pull_requests = sum(
                (self.fetch_pull_requests(repo) for repo in repo_tags), []
            )
            log.debug(" Found %i total.", len(pull_requests))

            closed = ['rejected', 'fulfilled']

            def not_resolved(tup: tuple[str, dict[str, Any]]) -> bool:
                return tup[1]['state'] not in closed

            pull_requests = list(filter(not_resolved, pull_requests))
            pull_requests = list(filter(self.include, pull_requests))
            log.debug(" Pruned down to %i", len(pull_requests))

            for tag, issue in pull_requests:
                tagParts = tag.split('/')
                projectName = tagParts[1]
                if self.config.project_owner_prefix:
                    projectName = tagParts[0] + "." + projectName
                url = self.BASE_URL + '/'.join(
                    issue['links']['html']['href'].split('/')[3:]
                ).replace('pullrequests', 'pullrequest')
                extras = {
                    'project': projectName,
                    'url': url,
                    'annotations': self.get_annotations(tag, issue, url),
                }
                yield self.process_record(issue, extras)
