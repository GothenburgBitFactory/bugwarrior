from collections.abc import Iterator
import logging
import typing
from typing import Any

from pydantic import computed_field
import requests
import urllib3

from bugwarrior import config
from bugwarrior.services import Client, Issue, Service

log = logging.getLogger(__name__)


class YoutrackConfig(config.ServiceConfig):
    service: typing.Literal['youtrack']
    host: config.NoSchemeUrl
    login: str
    token: str

    anonymous: bool = False
    port: typing.Optional[int] = None
    use_https: bool = True
    verify_ssl: bool = True
    incloud_instance: bool = False
    query: str = 'for:me #Unresolved'
    query_limit: int = 100
    import_tags: bool = True
    tag_template: str = '{{tag|lower}}'

    only_if_assigned: config.UnsupportedOption[str] = ''
    also_unassigned: config.UnsupportedOption[bool] = False

    @computed_field
    @property
    def base_url(self) -> str:
        if self.use_https:
            scheme = 'https'
            port = 443
        else:
            scheme = 'http'
            port = 80
        port = self.port or port
        base_url = f'{scheme}://{self.host}:{port}'
        if self.incloud_instance:
            base_url += '/youtrack'
        return base_url


class YoutrackIssue(Issue):
    ISSUE = 'youtrackissue'
    SUMMARY = 'youtracksummary'
    URL = 'youtrackurl'
    PROJECT = 'youtrackproject'
    NUMBER = 'youtracknumber'

    UDAS = {
        ISSUE: {'type': 'string', 'label': 'YouTrack Issue'},
        SUMMARY: {'type': 'string', 'label': 'YouTrack Summary'},
        URL: {'type': 'string', 'label': 'YouTrack URL'},
        PROJECT: {'type': 'string', 'label': 'YouTrack Project'},
        NUMBER: {'type': 'string', 'label': 'YouTrack Project Issue Number'},
    }
    UNIQUE_KEY = (URL,)
    PRIORITY_MAP: dict[str, config.Priority] = {}

    def to_taskwarrior(self) -> dict[str, Any]:
        return {
            'project': self.get_project(),
            'priority': self.get_priority(),
            'tags': self.get_tags(),
            self.ISSUE: self.get_issue(),
            self.SUMMARY: self.get_issue_summary(),
            self.URL: self.get_issue_url(),
            self.PROJECT: self.get_project(),
            self.NUMBER: self.get_number_in_project(),
        }

    def get_issue(self) -> str:
        return (self.get_project() or '') + '-' + str(self.get_number_in_project())

    def get_issue_summary(self) -> str | None:
        return self.record.get('summary')

    def get_issue_url(self) -> str:
        return "%s/issue/%s" % (self.config.base_url, self.get_issue())

    def get_project(self) -> str | None:
        return self.record.get('project', {}).get('shortName')

    def get_number_in_project(self) -> int | None:
        return self.record.get('numberInProject')

    def get_default_description(self) -> str:
        return self.build_default_description(
            title=self.get_issue_summary() or '',
            url=self.get_issue_url(),
            number=self.get_issue(),
            cls='issue',
        )

    def get_tags(self) -> list[str]:
        return self.get_tags_from_labels(
            [tag['name'] for tag in self.record.get('tags', [])],
            toggle_option='import_tags',
            template_option='tag_template',
            template_variable='tag',
        )


class YoutrackService(Service[YoutrackIssue]):
    API_VERSION = 1.0
    ISSUE_CLASS = YoutrackIssue
    CONFIG_SCHEMA = YoutrackConfig

    def __init__(
        self, config: YoutrackConfig, main_config: config.MainSectionConfig
    ) -> None:
        super().__init__(config, main_config)

        self.rest_url = self.config.base_url + '/api'

        self.session = requests.Session()
        self.session.headers['Accept'] = 'application/json'
        if not self.config.verify_ssl:
            urllib3.disable_warnings()
            self.session.verify = False

        token = self.get_secret('token', self.config.login)
        self.session.headers['Authorization'] = f'Bearer {token}'

    @staticmethod
    def get_keyring_service(config: YoutrackConfig) -> str:
        return f"youtrack://{config.login}@{config.host}"

    def issues(self) -> Iterator[YoutrackIssue]:
        params = {
            'query': self.config.query,
            'max': self.config.query_limit,
            'fields': 'id,summary,project(shortName),numberInProject,tags(name)',
        }
        resp = self.session.get(self.rest_url + '/issues', params=params)
        issues = Client.json_response(resp)
        log.debug(" Found %i total.", len(issues))

        for issue in issues:
            yield self.get_issue_for_record(issue)
