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
    REVIEWS = 'gerritreviews'    

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
        REVIEWS: {
            'type': 'string',
            'label': 'Gerrit Reviews',
        },
    }
    UNIQUE_KEY = (URL, )

    def _get_reviews(self):
        reviews = self.record['labels']['Code-Review']['all']
        return ' '.join([str(r['value']) for r in reviews if r['value'] != 0])

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
            self.REVIEWS: self._get_reviews(),
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
        self.ssl_ca_path = self.config.get('ssl_ca_path', None)
        self.session = requests.session()
        self.session.headers.update({
            'Accept': 'application/json',
            'Accept-Encoding': 'gzip',
        })
        self.query_string = self.config.get(
            'query',
            'is:open+is:reviewer'
        ) + '&o=DETAILED_LABELS&o=MESSAGES&o=DETAILED_ACCOUNTS'

        if self.ssl_ca_path:
            self.session.verify = os.path.expanduser(self.ssl_ca_path)

        # uses digest authentication if supported by the server, fallback to basic
        # gerrithub.io supports only basic
        response = self.session.head(self.url + '/a/')
        if 'digest' in response.headers.get('www-authenticate', '').lower():
            self.session.auth = requests.auth.HTTPDigestAuth(
                self.username, self.password)
        else:
            self.session.auth = requests.auth.HTTPBasicAuth(
                self.username, self.password)

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
            if option not in service_config:
                die("[%s] has no 'gerrit.%s'" % (target, option))

        IssueService.validate_config(service_config, target)

    def issues(self):
        # Construct the whole url by hand here, because otherwise requests will
        # percent-encode the ':' characters, which gerrit doesn't like.
        url = self.url + '/a/changes/?q=' + self.query_string
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
            yield self.get_issue_for_record(change, extra)

    def build_url(self, change):
        return '%s/#/c/%i/' % (self.url, change['_number'])

    def annotations(self, change):
        entries = []
        for item in change['messages']:
            for key in ['name', 'username', 'email']:
                if key in item['author']:
                    username = item['author'][key]
                    break
            else:
                username = item['author']['_account_id']
            # Gerrit messages are really messy
            message = item['message']\
                .lstrip('Patch Set ')\
                .lstrip("%s:" % item['_revision_number'])\
                .strip()\
                .replace('\n', ' ')
            entries.append((username, message,))

        return self.build_annotations(entries, self.build_url(change))
