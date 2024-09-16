import typing

import pydantic.v1
import requests
import typing_extensions

from bugwarrior import config
from bugwarrior.services import IssueService, Issue, ServiceClient

import logging

log = logging.getLogger(__name__)


class YoutrackConfig(config.ServiceConfig):
    service: typing_extensions.Literal['youtrack']
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

    # added during validation (computed field support will land in pydantic-2)
    base_url: str = ''

    @pydantic.v1.root_validator
    def compute_base_url(cls, values):
        if values['use_https']:
            scheme = 'https'
            port = 443
        else:
            scheme = 'http'
            port = 80
        port = values['port'] or port
        values['base_url'] = f'{scheme}://{values["host"]}:{port}'
        if values['incloud_instance']:
            values['base_url'] += '/youtrack'

        return values


class YoutrackIssue(Issue):
    ISSUE = 'youtrackissue'
    SUMMARY = 'youtracksummary'
    URL = 'youtrackurl'
    PROJECT = 'youtrackproject'
    NUMBER = 'youtracknumber'

    UDAS = {
        ISSUE: {
            'type': 'string',
            'label': 'YouTrack Issue'
        },
        SUMMARY: {
            'type': 'string',
            'label': 'YouTrack Summary',
        },
        URL: {
            'type': 'string',
            'label': 'YouTrack URL',
        },
        PROJECT: {
            'type': 'string',
            'label': 'YouTrack Project'
        },
        NUMBER: {
            'type': 'string',
            'label': 'YouTrack Project Issue Number'
        },
    }
    UNIQUE_KEY = (URL,)

    def to_taskwarrior(self):
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

    def get_issue(self):
        return self.get_project() + '-' + str(self.get_number_in_project())

    def get_issue_summary(self):
        return self.record.get('summary')

    def get_issue_url(self):
        return "%s/issue/%s" % (
            self.config.base_url, self.get_issue()
        )

    def get_project(self):
        return self.record.get('project').get('shortName')

    def get_number_in_project(self):
        return self.record.get('numberInProject')

    def get_default_description(self):
        return self.build_default_description(
            title=self.get_issue_summary(),
            url=self.get_issue_url(),
            number=self.get_issue(),
            cls='issue',
        )

    def get_tags(self):
        return self.get_tags_from_labels(
            [tag['name'] for tag in self.record.get('tags', [])],
            toggle_option='import_tags',
            template_option='tag_template',
            template_variable='tag',
        )


class YoutrackService(IssueService, ServiceClient):
    ISSUE_CLASS = YoutrackIssue
    CONFIG_SCHEMA = YoutrackConfig

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)

        self.rest_url = self.config.base_url + '/api'

        self.session = requests.Session()
        self.session.headers['Accept'] = 'application/json'
        if not self.config.verify_ssl:
            requests.packages.urllib3.disable_warnings()
            self.session.verify = False

        token = self.get_password('token', self.config.login)
        self.session.headers['Authorization'] = f'Bearer {token}'

    @staticmethod
    def get_keyring_service(config):
        return f"youtrack://{config.login}@{config.host}"

    def get_owner(self, issue):
        # TODO
        raise NotImplementedError(
            "This service has not implemented support for 'only_if_assigned'.")

    def issues(self):
        params = {
            'query': self.config.query,
            'max': self.config.query_limit,
            'fields': 'id,summary,project(shortName),numberInProject,tags(name)'
        }
        resp = self.session.get(self.rest_url + '/issues', params=params)
        issues = self.json_response(resp)
        log.debug(" Found %i total.", len(issues))

        for issue in issues:
            yield self.get_issue_for_record(issue)
