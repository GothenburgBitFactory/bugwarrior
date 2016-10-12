import six
import requests

from bugwarrior.config import die
from bugwarrior.services import Issue, IssueService, ServiceClient

import logging
log = logging.getLogger(__name__)


class RedMineClient(ServiceClient):
    def __init__(self, url, key, auth):
        self.url = url
        self.key = key
        self.auth = auth

    def find_issues(self, user_id=None):
        args = {"limit": 100}
        if user_id is not None:
            args["assigned_to_id"] = user_id
        return self.call_api("/issues.json", args)["issues"]

    def call_api(self, uri, params):
        url = self.url.rstrip("/") + uri
        kwargs = {
            'headers': {'X-Redmine-API-Key': self.key},
            'params': params}

        if self.auth:
            kwargs['auth'] = self.auth

        return self.json_response(requests.get(url, **kwargs))


class RedMineIssue(Issue):
    URL = 'redmineurl'
    SUBJECT = 'redminesubject'
    ID = 'redmineid'

    UDAS = {
        URL: {
            'type': 'string',
            'label': 'Redmine URL',
        },
        SUBJECT: {
            'type': 'string',
            'label': 'Redmine Subject',
        },
        ID: {
            'type': 'string',
            'label': 'Redmine ID',
        },
    }
    UNIQUE_KEY = (URL, )

    PRIORITY_MAP = {
        'Low': 'L',
        'Normal': 'M',
        'High': 'H',
        'Urgent': 'H',
        'Immediate': 'H',
    }

    def to_taskwarrior(self):
        return {
            'project': self.get_project_name(),
            'priority': self.get_priority(),

            self.URL: self.get_issue_url(),
            self.SUBJECT: self.record['subject'],
            self.ID: self.record['id']
        }

    def get_priority(self):
        return self.PRIORITY_MAP.get(
            self.record.get('priority', {}).get('Name'),
            self.origin['default_priority']
        )

    def get_issue_url(self):
        return (
            self.origin['url'] + "/issues/" + six.text_type(self.record["id"])
        )

    def get_project_name(self):
        if self.origin['project_name']:
            return self.origin['project_name']
        return self.record["project"]["name"]

    def get_default_description(self):
        return self.build_default_description(
            title=self.record['subject'],
            url=self.get_processed_url(self.get_issue_url()),
            number=self.record['id'],
            cls='issue',
        )


class RedMineService(IssueService):
    ISSUE_CLASS = RedMineIssue
    CONFIG_PREFIX = 'redmine'

    def __init__(self, *args, **kw):
        super(RedMineService, self).__init__(*args, **kw)

        self.url = self.config_get('url').rstrip("/")
        self.key = self.config_get('key')
        self.user_id = self.config_get('user_id')

        login = self.config_get_default('login')
        if login:
            password = self.config_get_password('password', login)
        auth = (login, password) if (login and password) else None
        self.client = RedMineClient(self.url, self.key, auth)

        self.project_name = self.config_get_default('project_name')

    def get_service_metadata(self):
        return {
            'project_name': self.project_name,
            'url': self.url,
        }

    @classmethod
    def get_keyring_service(cls, config, section):
        url = config.get(section, cls._get_key('url'))
        login = config.get(section, cls._get_key('login'))
        user_id = config.get(section, cls._get_key('user_id'))
        return "redmine://%s@%s/%s" % (login, url, user_id)

    @classmethod
    def validate_config(cls, config, target):
        for k in ('redmine.url', 'redmine.key', 'redmine.user_id'):
            if not config.has_option(target, k):
                die("[%s] has no '%s'" % (target, k))

        IssueService.validate_config(config, target)

    def issues(self):
        issues = self.client.find_issues(self.user_id)
        log.debug(" Found %i total.", len(issues))

        for issue in issues:
            yield self.get_issue_for_record(issue)
