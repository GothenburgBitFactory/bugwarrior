from collections.abc import Iterator
import datetime
import logging
import typing
from typing import Any

from pydantic import AliasChoices, Field, model_validator
import requests

from bugwarrior import config
from bugwarrior.services import Issue, Service

log = logging.getLogger(__name__)


class PagureConfig(config.ServiceConfig):
    service: typing.Literal['pagure']
    KEYRING_SERVICE = "pagure://{base_url}"
    base_url: config.StrippedTrailingSlashUrl

    # conditionally required
    tag: str = ''
    repo: str = ''

    # optional
    include_repos: config.ConfigList = []
    exclude_repos: config.ConfigList = []
    import_labels_as_tags: bool = Field(
        False, validation_alias=AliasChoices('import_labels_as_tags', 'import_tags')
    )
    label_template: str = Field(
        '{{label}}', validation_alias=AliasChoices('label_template', 'tag_template')
    )

    @model_validator(mode='before')
    @classmethod
    def deprecate_legacy_tag_options(cls, values: Any) -> Any:
        if not isinstance(values, dict):
            return values

        if 'import_tags' in values:
            log.warning('import_tags is deprecated in favor of import_labels_as_tags')
        if 'tag_template' in values:
            log.warning('tag_template is deprecated in favor of label_template')

        return values

    @model_validator(mode='after')
    def require_tag_or_repo(self) -> "PagureConfig":
        if not self.tag and not self.repo:
            raise ValueError('section requires one of:\n    tag\n    repo')
        return self


class PagureIssue(Issue):
    TITLE = 'paguretitle'
    DATE_CREATED = 'paguredatecreated'
    URL = 'pagureurl'
    REPO = 'pagurerepo'
    TYPE = 'paguretype'
    ID = 'pagureid'

    UDAS = {
        TITLE: {'type': 'string', 'label': 'Pagure Title'},
        DATE_CREATED: {'type': 'date', 'label': 'Pagure Created'},
        REPO: {'type': 'string', 'label': 'Pagure Repo Slug'},
        URL: {'type': 'string', 'label': 'Pagure URL'},
        TYPE: {'type': 'string', 'label': 'Pagure Type'},
        ID: {'type': 'numeric', 'label': 'Pagure Issue/PR #'},
    }
    UNIQUE_KEY = (URL, TYPE)

    def to_taskwarrior(self) -> dict[str, Any]:
        if self.extra['type'] == 'pull_request':
            priority = 'H'
        else:
            priority = self.config.default_priority

        return {
            'project': self.extra['project'],
            'priority': priority,
            'annotations': self.extra.get('annotations', []),
            'tags': self.get_tags(),
            self.URL: self.record['html_url'],
            self.REPO: self.record['repo'],
            self.TYPE: self.extra['type'],
            self.TITLE: self.record['title'],
            self.ID: self.record['id'],
            self.DATE_CREATED: datetime.datetime.fromtimestamp(
                int(self.record['date_created']), datetime.timezone.utc
            ),
        }

    def get_tags(self) -> list[str]:
        return self.get_tags_from_labels(self.record.get('tags', []))

    def get_default_description(self) -> str:
        return self.build_default_description(
            title=self.record['title'],
            url=self.record['html_url'],
            number=self.record['id'],
            cls=self.extra['type'],
        )


class PagureService(Service[PagureIssue]):
    API_VERSION = 2.0
    ISSUE_CLASS = PagureIssue
    CONFIG_SCHEMA = PagureConfig

    def __init__(
        self, config: PagureConfig, main_config: config.MainSectionConfig
    ) -> None:
        super().__init__(config, main_config)

        self.session = requests.Session()

    def get_issues(
        self, repo: str, keys: tuple[str, str]
    ) -> list[tuple[str, dict[str, Any]]]:
        """Grab all the issues"""
        key1, key2 = keys
        key3 = key1[:-1]  # Just the singular form of key1

        url = self.config.base_url + "/api/0/" + repo + "/" + key1
        response = self.session.get(url, params=dict(status='Open'))

        if not bool(response):
            error = response.json()
            code = error['error_code']
            if code == 'ETRACKERDISABLED':
                return []
            else:
                raise OSError('Failed to talk to %r %r' % (url, error))

        issues = []
        for result in response.json()[key2]:
            idx = str(result['id'])
            result['html_url'] = "/".join([self.config.base_url, repo, key3, idx])
            issues.append((repo, result))

        return issues

    def annotations(self, issue: dict[str, Any]) -> list[str]:
        url = issue['html_url']
        return self.build_annotations(
            ((c['user']['name'], c['comment']) for c in issue['comments']), url
        )

    def get_owner(self, issue: tuple[str, dict[str, Any]]) -> str | None:
        if issue[1]['assignee']:
            return issue[1]['assignee']['name']

    def include(self, issue: tuple[str, dict[str, Any]]) -> bool:
        """Return true if the issue in question should be included"""
        if self.config.only_if_assigned:
            owner = self.get_owner(issue)
            include_owners: list[str | None] = [self.config.only_if_assigned]

            if self.config.also_unassigned:
                include_owners.append(None)

            return owner in include_owners

        return True

    def filter_repos(self, repo: str) -> bool:
        if repo in self.config.exclude_repos:
            return False

        if self.config.include_repos:
            if repo in self.config.include_repos:
                return True
            else:
                return False

        return True

    def issues(self) -> Iterator[PagureIssue]:
        if self.config.tag:
            url = self.config.base_url + "/api/0/projects?tags=" + self.config.tag
            response = self.session.get(url)
            if not bool(response):
                raise OSError('Failed to talk to %r %r' % (url, response))

            all_repos = [r['name'] for r in response.json()['projects']]
        else:
            all_repos = [self.config.repo]

        repos = filter(self.filter_repos, all_repos)

        issues = []
        for repo in repos:
            issues.extend(self.get_issues(repo, ('issues', 'issues')))
            issues.extend(self.get_issues(repo, ('pull-requests', 'requests')))

        log.debug(" Found %i issues.", len(issues))
        issues = list(filter(self.include, issues))
        log.debug(" Pruned down to %i issues.", len(issues))

        for repo, issue in issues:
            # Stuff this value into the upstream dict for:
            # https://pagure.com/ralphbean/bugwarrior/issues/159
            issue['repo'] = repo

            issue_obj = self.get_issue_for_record(issue)
            extra = {
                'project': repo,
                'type': 'pull_request' if 'branch' in issue else 'issue',
                'annotations': self.annotations(issue),
            }
            issue_obj.extra.update(extra)
            yield issue_obj
