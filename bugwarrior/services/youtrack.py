from __future__ import absolute_import
import re
import six

import requests
from jinja2 import Template

from bugwarrior.config import asbool, die
from bugwarrior.services import IssueService, Issue, ServiceClient

import logging

log = logging.getLogger(__name__)


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
        tags = []

        if not self.origin['import_tags']:
            return tags

        context = self.record.copy()
        tag_template = Template(self.origin['tag_template'])

        for tag_dict in self.record.get('tag', []):
            context.update({
                'tag': re.sub(r'[^a-zA-Z0-9]', '_', tag_dict['value'])
            })
            tags.append(
                tag_template.render(context)
            )

        return tags


class YoutrackService(IssueService, ServiceClient):
    ISSUE_CLASS = YoutrackIssue
    CONFIG_PREFIX = 'youtrack'

    def __init__(self, *args, **kw):
        super(YoutrackService, self).__init__(*args, **kw)

        self.host = self.config.get('host')
        if self.config.get('use_https', default=True, to_type=asbool):
            self.scheme = 'https'
            self.port = '443'
        else:
            self.scheme = 'http'
            self.port = '80'
        self.port = self.config.get('port', self.port)
        self.base_url = '%s://%s:%s' % (self.scheme, self.host, self.port)
        self.rest_url = self.base_url + '/rest'

        self.session = requests.Session()
        self.session.headers['Accept'] = 'application/json'
        self.verify_ssl = self.config.get('verify_ssl', default=True, to_type=asbool)
        if not self.verify_ssl:
            requests.packages.urllib3.disable_warnings()
            self.session.verify = False

        login = self.config.get('login')
        password = self.get_password('password', login)
        if not self.config.get('anonymous', False):
            self._login(login, password)

        self.query = self.config.get('query', default='for:me #Unresolved')
        self.query_limit = self.config.get('query_limit', default="100")

        self.import_tags = self.config.get(
            'import_tags', default=True, to_type=asbool
        )
        self.tag_template = self.config.get(
            'tag_template', default='{{tag|lower}}', to_type=six.text_type
        )

    def _login(self, login, password):
        params = {'login': login, 'password': password}
        resp = self.session.post(self.rest_url + "/user/login", params)
        if resp.status_code != 200:
            raise RuntimeError("YouTrack responded with %s" % resp)
        self.session.headers['Cookie'] = resp.headers['set-cookie']

    @staticmethod
    def get_keyring_service(service_config):
        host = service_config.get('host')
        login = service_config.get('login')
        return "youtrack://%s@%s" % (login, host)

    def get_service_metadata(self):
        return {
            'base_url': self.base_url,
            'import_tags': self.import_tags,
            'tag_template': self.tag_template,
        }

    @classmethod
    def validate_config(cls, service_config, target):
        for k in ('login', 'password', 'host'):
            if k not in service_config:
                die("[%s] has no 'youtrack.%s'" % (target, k))

        IssueService.validate_config(service_config, target)

    def issues(self):
        params = {'filter': self.query, 'max': self.query_limit}
        resp = self.session.get(self.rest_url + '/issue', params=params)
        issues = self.json_response(resp)['issue']
        log.debug(" Found %i total.", len(issues))

        for issue in issues:
            yield self.get_issue_for_record(issue)
