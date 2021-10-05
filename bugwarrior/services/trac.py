from future import standard_library
standard_library.install_aliases()
from builtins import filter
from builtins import map
from builtins import range
import csv
import io as StringIO
import urllib.parse

import offtrac
import requests
import typing_extensions

from bugwarrior import config
from bugwarrior.services import Issue, IssueService

import logging
log = logging.getLogger(__name__)


class TracConfig(config.ServiceConfig, prefix='trac'):
    service: typing_extensions.Literal['trac']
    base_uri: config.NoSchemeUrl

    scheme: str = 'https'
    no_xmlrpc: bool = False
    username: str = ''
    password: str = ''


class TracIssue(Issue):
    SUMMARY = 'tracsummary'
    URL = 'tracurl'
    NUMBER = 'tracnumber'
    COMPONENT = 'traccomponent'

    UDAS = {
        SUMMARY: {
            'type': 'string',
            'label': 'Trac Summary',
        },
        URL: {
            'type': 'string',
            'label': 'Trac URL',
        },
        NUMBER: {
            'type': 'numeric',
            'label': 'Trac Number',
        },
        COMPONENT: {
            'type': 'string',
            'label': 'Trac Component',
        },
    }
    UNIQUE_KEY = (URL, )

    PRIORITY_MAP = {
        'trivial': 'L',
        'minor': 'L',
        'major': 'M',
        'critical': 'H',
        'blocker': 'H',
    }

    def to_taskwarrior(self):
        return {
            'project': self.extra['project'],
            'priority': self.get_priority(),
            'annotations': self.extra['annotations'],

            self.URL: self.record['url'],
            self.SUMMARY: self.record['summary'],
            self.NUMBER: self.record['number'],
            self.COMPONENT: self.record['component'],
        }

    def get_default_description(self):

        if 'number' in self.record:
            number = self.record['number']
        else:
            number = self.record['id']

        return self.build_default_description(
            title=self.record['summary'],
            url=self.get_processed_url(self.record['url']),
            number=number,
            cls='issue'
        )

    def get_priority(self):
        return self.PRIORITY_MAP.get(
            self.record.get('priority'),
            self.origin['default_priority']
        )


class TracService(IssueService):
    ISSUE_CLASS = TracIssue
    CONFIG_SCHEMA = TracConfig

    def __init__(self, *args, **kw):
        super(TracService, self).__init__(*args, **kw)
        if self.config.username:
            password = self.get_password('password', self.config.username)

            auth = urllib.parse.quote_plus(
                f'{self.config.username}:{password}@')
        else:
            auth = ''

        self.trac = None
        uri = f'{self.config.scheme}://{auth}{self.config.base_uri}/'
        if self.config.no_xmlrpc:
            self.uri = uri
        else:
            self.trac = offtrac.TracServer(uri + 'login/xmlrpc')

    @staticmethod
    def get_keyring_service(config):
        return f"https://{config.username}@{config.base_uri}/"

    def annotations(self, tag, issue, issue_obj):
        annotations = []
        # without offtrac, we can't get issue comments
        if self.trac is None:
            return annotations
        changelog = self.trac.server.ticket.changeLog(issue['number'])
        for time, author, field, oldvalue, newvalue, permament in changelog:
            if field == 'comment':
                annotations.append((author, newvalue, ))

        url = issue_obj.get_processed_url(issue['url'])
        return self.build_annotations(annotations, url)

    def get_owner(self, issue):
        tag, issue = issue
        return issue.get('owner', None) or None

    def issues(self):
        base_url = "https://" + self.config.base_uri
        if self.trac:
            tickets = self.trac.query_tickets('status!=closed&max=0')
            tickets = list(map(self.trac.get_ticket, tickets))
            issues = [(self.target, ticket[3]) for ticket in tickets]
            for i in range(len(issues)):
                issues[i][1]['url'] = "%s/ticket/%i" % (base_url, tickets[i][0])
                issues[i][1]['number'] = tickets[i][0]
        else:
            resp = requests.get(
                self.uri + 'query',
                params={
                    'status': '!closed',
                    'max': '0',
                    'format': 'csv',
                    'col': ['id', 'summary', 'owner', 'priority', 'component'],
                })
            if resp.status_code != 200:
                raise RuntimeError("Trac responded with %s" % resp)
            # strip Trac's bogus BOM
            text = resp.text[1:].lstrip(u'\ufeff')
            tickets = list(csv.DictReader(StringIO.StringIO(text.encode('utf-8'))))
            issues = [(self.target, ticket) for ticket in tickets]
            for i in range(len(issues)):
                issues[i][1]['url'] = "%s/ticket/%s" % (base_url, tickets[i]['id'])
                issues[i][1]['number'] = int(tickets[i]['id'])

        log.debug(" Found %i total.", len(issues))

        issues = list(filter(self.include, issues))
        log.debug(" Pruned down to %i", len(issues))

        for project, issue in issues:
            issue_obj = self.get_issue_for_record(issue)
            extra = {
                'annotations': self.annotations(project, issue, issue_obj),
                'project': project,
            }
            issue_obj.update_extra(extra)
            yield issue_obj
