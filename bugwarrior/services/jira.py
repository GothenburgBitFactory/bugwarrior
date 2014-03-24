from __future__ import absolute_import

from jira.client import JIRA

from bugwarrior.config import die, get_service_password
from bugwarrior.services import IssueService, Issue


class JiraIssue(Issue):
    SUMMARY = 'jirasummary'
    URL = 'jiraurl'
    FOREIGN_ID = 'jiraid'

    UDAS = {
        SUMMARY: {
            'type': 'string',
            'label': 'Jira Summary'
        },
        URL: {
            'type': 'string',
            'label': 'Jira URL',
        },
        FOREIGN_ID: {
            'type': 'string',
            'label': 'Jira Issue ID'
        }
    }
    UNIQUE_KEY = (URL, )

    PRIORITY_MAP = {
        'Trivial': 'L',
        'Minor': 'L',
        'Major': 'M',
        'Critical': 'H',
        'Blocker': 'H',
    }

    def to_taskwarrior(self):
        return {
            'project': self.get_project(),
            'priority': self.get_priority(),
            'annotations': self.get_annotations(),

            self.URL: self.get_url(),
            self.FOREIGN_ID: self.record['key'],
            self.SUMMARY: self.get_summary(),
        }

    def get_annotations(self):
        return self.extra.get('annotations', [])

    def get_project(self):
        return self.record['key'].rsplit('-', 1)[0]

    def get_number(self):
        return self.record['key'].rsplit('-', 1)[1]

    def get_url(self):
        return self.origin['url'] + '/browse/' + self.record['key']

    def get_summary(self):
        if self.extra.get('jira_version') == 4:
            return self.record['fields']['summary']['value']
        return self.record['fields']['summary']

    def get_priority(self):
        value = self.record['fields'].get('priority')
        if isinstance(value, dict):
            value = value.get('name')
        elif value:
            value = str(value)

        return self.PRIORITY_MAP.get(value, self.origin['default_priority'])

    def get_default_description(self):
        return self.build_default_description(
            title=self.get_summary(),
            url=self.get_processed_url(self.get_url()),
            number=self.get_number(),
            cls='issue',
        )


class JiraService(IssueService):
    ISSUE_CLASS = JiraIssue
    CONFIG_PREFIX = 'jira'

    def __init__(self, *args, **kw):
        super(JiraService, self).__init__(*args, **kw)
        self.username = self.config_get('username')
        self.url = self.config_get('base_uri')
        password = self.config_get('password')
        if not password or password.startswith("@oracle:"):
            service = "jira://%s@%s" % (self.username, self.url)
            password = get_service_password(
                service, self.username,
                oracle=password,
                interactive=self.config.interactive
            )

        default_query = 'assignee=' + self.username + \
            ' AND status != closed and status != resolved'
        self.query = self.config_get_default('query', default_query)
        self.jira = JIRA(
            options={
                'server': self.config_get('base_uri'),
                'rest_api_version': 'latest',
            },
            basic_auth=(self.username, password)
        )

    def get_service_metadata(self):
        return {
            'url': self.url,
        }

    @classmethod
    def validate_config(cls, config, target):
        for option in ('jira.username', 'jira.password', 'jira.base_uri'):
            if not config.has_option(target, option):
                die("[%s] has no '%s'" % (target, option))

        IssueService.validate_config(config, target)

    def annotations(self, issue):
        comments = self.jira.comments(issue)

        if not comments:
            return []
        else:
            return self.build_annotations(
                (
                    comment.author.name,
                    comment.body
                ) for comment in comments
            )

    def issues(self):
        cases = self.jira.search_issues(self.query, maxResults=-1)

        jira_version = 5
        if self.config.has_option(self.target, 'jira.version'):
            jira_version = self.config.getint(self.target, 'jira.version')

        for case in cases:
            extra = {
                'jira_version': jira_version,
            }
            if jira_version > 4:
                extra.update({
                    'annotations': self.annotations(case.key)
                })
            yield self.get_issue_for_record(case.raw)
