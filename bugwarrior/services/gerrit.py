from __future__ import absolute_import

import json
import os

import requests

from bugwarrior.config import die
from bugwarrior.services import IssueService, Issue, ServiceClient


class GerritIssue(Issue):
    SUMMARY = 'gerritsummary'
    URL = 'gerriturl'
    FOREIGN_ID = 'gerritid'
    BRANCH = 'gerritbranch'
    TOPIC = 'gerrittopic'

    UDAS = {
        SUMMARY: {
            'type': 'string',
            'label': 'Gerrit Summary'
        },
        URL: {
            'type': 'string',
            'label': 'Gerrit URL',
        },
        FOREIGN_ID: {
            'type': 'numeric',
            'label': 'Gerrit Change ID'
        },
        BRANCH: {
            'type': 'string',
            'label': 'Gerrit Branch',
        },
        TOPIC: {
            'type': 'string',
            'label': 'Gerrit Topic',
        },
    }
    UNIQUE_KEY = (URL, )

    def to_taskwarrior(self):
        return {
            'project': self.record['project'],
            'annotations': self.extra['annotations'],
            self.URL: self.extra['url'],

            'priority': self.origin['default_priority'],
            'tags': [],
            self.FOREIGN_ID: self.record['_number'],
            self.SUMMARY: self.record['subject'],
            self.BRANCH: self.record['branch'],
            self.TOPIC: self.record.get('topic', 'notopic'),
        }

    def get_default_description(self):
        return self.build_default_description(
            title=self.record['subject'],
            url=self.get_processed_url(self.extra['url']),
            number=self.record['_number'],
            cls='pull_request',
        )


class GerritService(IssueService, ServiceClient):
    ISSUE_CLASS = GerritIssue
    CONFIG_PREFIX = 'gerrit'

    def __init__(self, *args, **kw):
        super(GerritService, self).__init__(*args, **kw)
        self.url = self.config.get('base_uri').strip('/')
        self.username = self.config.get('username')
        self.password = self.get_password('password', self.username)
        self.ssl_ca_path = self.config.get_default('ssl_ca_path', None)
        self.session = requests.session()
        self.session.headers.update({
            'Accept': 'application/json',
            'Accept-Encoding': 'gzip',
        })

        self.session.auth = requests.auth.HTTPDigestAuth(
            self.username, self.password)

        if self.ssl_ca_path != None:
            self.session.verify = os.path.expanduser(self.ssl_ca_path)

    @staticmethod
    def get_keyring_service(service_config):
        base_uri = service_config.get('base_uri')
        return "gerrit://%s" % base_uri

    def get_service_metadata(self):
        return {
            'url': self.url,
        }

    @classmethod
    def validate_config(cls, service_config, target):
        for option in ('username', 'password', 'base_uri'):
            if not service_config.has(option):
                die("[%s] has no 'gerrit.%s'" % (target, option))

        IssueService.validate_config(service_config, target)

    def issues(self):
        # Construct the whole url by hand here, because otherwise requests will
        # percent-encode the ':' characters, which gerrit doesn't like.
        url = self.url + '/a/changes/' + \
            '?q=is:open+is:reviewer' + \
            '&o=MESSAGES&o=DETAILED_ACCOUNTS'
        response = self.session.get(url)
        # The response has some ")]}'" garbage prefixed.
        body = response.text[4:]
        changes = json.loads(body)

        for change in changes:
            extra = {
                'url': self.build_url(change),
                'annotations': self.annotations(change),
            }
            yield self.get_issue_for_record(change, extra)

    def build_url(self, change):
        return '%s/#/c/%i/' % (self.url, change['_number'])

    def annotations(self, change):
        entries = []
        for item in change['messages']:
            username = item['author']['username']
            # Gerrit messages are really messy
            message = item['message']\
                .lstrip('Patch Set ')\
                .lstrip("%s:" % item['_revision_number'])\
                .strip()\
                .replace('\n', ' ')
            entries.append((username, message,))

        return self.build_annotations(entries, self.build_url(change))
