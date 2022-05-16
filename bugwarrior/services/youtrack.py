import typing

import requests
import typing_extensions

from bugwarrior import config
from bugwarrior.services import IssueService, Issue, ServiceClient

import logging

log = logging.getLogger(__name__)


class YoutrackConfig(config.ServiceConfig, prefix='youtrack'):
    service: typing_extensions.Literal['youtrack']
    host: config.NoSchemeUrl
    login: str
    password: str

    anonymous: bool = False
    port: typing.Optional[int] = None
    use_https: bool = True
    verify_ssl: bool = True
    incloud_instance: bool = False
    query: str = 'for:me #Unresolved'
    query_limit: int = 100
    import_tags: bool = True
    tag_template: str = '{{tag|lower}}'


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

    def _get_record_field(self, field_name):
        for field in self.record['field']:
            if field['name'] == field_name:
                return field

    def _get_record_field_value(self, field_name, field_value='value'):
        field = self._get_record_field(field_name)
        if field:
            return field[field_value]

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
        return self.record['id']

    def get_issue_summary(self):
        return self._get_record_field_value('summary')

    def get_issue_url(self):
        return "%s/issue/%s" % (
            self.origin['base_url'], self.get_issue()
        )

    def get_project(self):
        return self._get_record_field_value('projectShortName')

    def get_number_in_project(self):
        return int(self._get_record_field_value('numberInProject'))

    def get_default_description(self):
        return self.build_default_description(
            title=self.get_issue_summary(),
            url=self.get_processed_url(self.get_issue_url()),
            number=self.get_issue(),
            cls='issue',
        )

    def get_tags(self):
        return self.get_tags_from_labels(
            [tag['value'] for tag in self.record.get('tag', [])],
            toggle_option='import_tags',
            template_option='tag_template',
            template_variable='tag',
        )


class YoutrackService(IssueService, ServiceClient):
    ISSUE_CLASS = YoutrackIssue
    CONFIG_SCHEMA = YoutrackConfig

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)

        if self.config.use_https:
            scheme = 'https'
            port = 443
        else:
            scheme = 'http'
            port = 80
        port = self.config.port or port
        self.base_url = f'{scheme}://{self.config.host}:{port}'
        if self.config.incloud_instance:
            self.base_url += '/youtrack'
        self.rest_url = self.base_url + '/rest'

        self.session = requests.Session()
        self.session.headers['Accept'] = 'application/json'
        if not self.config.verify_ssl:
            requests.packages.urllib3.disable_warnings()
            self.session.verify = False

        password = self.get_password('password', self.config.login)
        if not self.config.anonymous:
            self._login(self.config.login, password)

    def _login(self, login, password):
        params = {'login': login, 'password': password}
        resp = self.session.post(self.rest_url + "/user/login", params)
        if resp.status_code != 200:
            raise RuntimeError("YouTrack responded with %s" % resp)
        self.session.headers['Cookie'] = resp.headers['set-cookie']

    @staticmethod
    def get_keyring_service(config):
        return f"youtrack://{config.login}@{config.host}"

    def get_service_metadata(self):
        return {
            'base_url': self.base_url,
            'import_tags': self.config.import_tags,
            'tag_template': self.config.tag_template,
        }

    def get_owner(self, issue):
        # TODO
        raise NotImplementedError(
            "This service has not implemented support for 'only_if_assigned'.")

    def issues(self):
        params = {'filter': self.config.query, 'max': self.config.query_limit}
        resp = self.session.get(self.rest_url + '/issue', params=params)
        issues = self.json_response(resp)['issue']
        log.debug(" Found %i total.", len(issues))

        for issue in issues:
            yield self.get_issue_for_record(issue)
