from __future__ import absolute_import

import megaplan

from bugwarrior.config import die
from bugwarrior.services import IssueService, Issue

import logging
log = logging.getLogger(__name__)


class MegaplanIssue(Issue):
    URL = 'megaplanurl'
    FOREIGN_ID = 'megaplanid'
    TITLE = 'megaplantitle'

    UDAS = {
        TITLE: {
            'type': 'string',
            'label': 'Megaplan Title',
        },
        URL: {
            'type': 'string',
            'label': 'Megaplan URL',
        },
        FOREIGN_ID: {
            'type': 'string',
            'label': 'Megaplan Issue ID'
        }
    }
    UNIQUE_KEY = (URL, )

    def to_taskwarrior(self):
        return {
            'project': self.get_project(),
            'priority': self.get_priority(),

            self.FOREIGN_ID: self.record['Id'],
            self.URL: self.get_issue_url(),
            self.TITLE: self.get_issue_title(),
        }

    def get_project(self):
        return self.origin['project_name']

    def get_default_description(self):
        return self.build_default_description(
            title=self.get_issue_title(),
            url=self.get_processed_url(self.get_issue_url()),
            number=self.record['Id'],
            cls='issue',
        )

    def get_issue_url(self):
        return "https://%s/task/%d/card/" % (
            self.origin['hostname'], self.record["Id"]
        )

    def get_issue_title(self):
        parts = self.record["Name"].split("|")
        return parts[-1].strip()

    def get_issue_id(self):
        if self.record["Id"] > 1000000:
            return self.record["Id"] - 1000000
        return self.record["Id"]


class MegaplanService(IssueService):
    ISSUE_CLASS = MegaplanIssue
    CONFIG_PREFIX = 'megaplan'

    def __init__(self, *args, **kw):
        super(MegaplanService, self).__init__(*args, **kw)

        self.hostname = self.config.get('hostname')
        _login = self.config.get('login')
        _password = self.get_password('password', _login)

        self.client = megaplan.Client(self.hostname)
        self.client.authenticate(_login, _password)

        self.project_name = self.config.get('project_name', self.hostname)

    @staticmethod
    def get_keyring_service(service_config):
        login = service_config.get('login')
        hostname = service_config.get('hostname')
        return "megaplan://%s@%s" % (login, hostname)

    def get_service_metadata(self):
        return {
            'project_name': self.project_name,
            'hostname': self.hostname,
        }

    @classmethod
    def validate_config(cls, service_config, target):
        for k in ('login', 'password', 'hostname'):
            if k not in service_config:
                die("[%s] has no 'mplan.%s'" % (target, k))

        IssueService.validate_config(service_config, target)

    def issues(self):
        issues = self.client.get_actual_tasks()
        log.debug(" Found %i total.", len(issues))

        for issue in issues:
            yield self.get_issue_for_record(issue)
