from collections.abc import Iterator
import json
import logging
import typing
from typing import Any

from pydantic import Field
import requests
import requests.auth

from bugwarrior import config
from bugwarrior.services import Issue, Service
from bugwarrior.task import Task, Udas

log = logging.getLogger(__name__)


class GerritConfig(config.ServiceConfig):
    service: typing.Literal['gerrit']
    KEYRING_SERVICE = "gerrit://{base_uri}"
    base_uri: config.StrippedTrailingSlashUrl
    username: str
    password: str

    ssl_ca_path: typing.Optional[config.ExpandedPath] = None
    query: str = 'is:open+is:reviewer'
    ignore_user_comments: config.ConfigList = []

    only_if_assigned: config.UnsupportedOption[str] = ''
    also_unassigned: config.UnsupportedOption[bool] = False


class GerritUdas(Udas):
    """Service-specific UDAs contributed by Gerrit."""

    UNIQUE_KEY = ('gerriturl',)

    gerritsummary: str = Field(title='Gerrit Summary')
    gerriturl: str = Field(title='Gerrit URL')
    gerritid: int = Field(title='Gerrit Change ID')
    gerritbranch: str = Field(title='Gerrit Branch')
    gerrittopic: str | None = Field(title='Gerrit Topic')
    gerritstatus: str | None = Field(title='Gerrit Status')
    gerritwip: int = Field(title='Gerrit Work in Progress')


class GerritTask(Task):
    udas: GerritUdas


class GerritIssue(Issue):
    def to_taskwarrior(self) -> GerritTask:
        return GerritTask(
            project=self.record['project'],
            annotations=self.extra['annotations'],
            priority=self.config.default_priority,
            tags=[],
            udas=GerritUdas(
                gerritsummary=self.record['subject'],
                gerriturl=self.extra['url'],
                gerritid=self.record['_number'],
                gerritbranch=self.record['branch'],
                gerrittopic=self.record.get('topic', 'notopic'),
                gerritstatus=self.record.get('status', ''),
                gerritwip=self.record.get('work_in_progress', 0),
            ),
        )

    def get_default_description(self) -> str:
        return self.build_default_description(
            title=self.record['subject'],
            url=self.extra['url'],
            number=self.record['_number'],
            cls='pull_request',
        )


class GerritService(Service):
    API_VERSION = 2.0
    ISSUE_CLASS = GerritIssue
    TASK_SCHEMA = GerritTask
    CONFIG_SCHEMA = GerritConfig

    def __init__(
        self, config: GerritConfig, main_config: config.MainSectionConfig
    ) -> None:
        super().__init__(config, main_config)
        self.password = self.get_secret('password', self.config.username)
        self.session = requests.session()
        self.session.headers.update(
            {'Accept': 'application/json', 'Accept-Encoding': 'gzip'}
        )
        self.query_string = self.config.query + '&o=MESSAGES&o=DETAILED_ACCOUNTS'

        if self.config.ssl_ca_path:
            self.session.verify = self.config.ssl_ca_path

        # uses digest authentication if supported by the server, fallback to basic
        # gerrithub.io supports only basic
        response = self.session.head(self.config.base_uri + '/a/')
        if 'digest' in response.headers.get('www-authenticate', '').lower():
            self.session.auth = requests.auth.HTTPDigestAuth(
                self.config.username, self.password
            )
        else:
            self.session.auth = requests.auth.HTTPBasicAuth(
                self.config.username, self.password
            )

    def issues(self) -> Iterator[Task]:
        # Construct the whole url by hand here, because otherwise requests will
        # percent-encode the ':' characters, which gerrit doesn't like.
        url = self.config.base_uri + '/a/changes/?q=' + self.query_string
        response = self.session.get(url)
        response.raise_for_status()
        # The response has some ")]}'" garbage prefixed.
        body = response.text[4:]
        changes = json.loads(body)

        for change in changes:
            extra = {
                'url': self.build_url(change),
                'annotations': self.annotations(change),
            }
            yield self.process_record(change, extra)

    def build_url(self, change: dict[str, Any]) -> str:
        return '%s/#/c/%i/' % (self.config.base_uri, change['_number'])

    def annotations(self, change: dict[str, Any]) -> list[str]:
        entries = []
        for item in change['messages']:
            for key in ['name', 'username', 'email']:
                if key in item['author']:
                    username = item['author'][key]
                    break
            else:
                username = item['author']['_account_id']
            if username in self.config.ignore_user_comments:
                log.debug(" ignoring comment from %s", username)
                continue
            message = (
                item['message']
                .lstrip('Patch Set ')
                .lstrip("%s:" % item['_revision_number'])
                .strip()
                .replace('\n', ' ')
            )
            entries.append((username, message))

        return self.build_annotations(entries, self.build_url(change))
