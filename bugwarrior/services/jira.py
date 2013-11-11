from __future__ import absolute_import

import time
from datetime import date

from twiggy import log
from jira.client import JIRA

from bugwarrior.services import IssueService
from bugwarrior.config import die, get_service_password


def get_priority(priority):
    if priority is None:
        return 'Major'
    else:
        return priority


class JiraService(IssueService):
    # A map of jira priorities to taskwarrior priorities
    priorities = {
        'Trivial': 'L',
        'Minor': 'L',
        'Major': 'M',
        'Critical': 'H',
        'Blocker': 'H',
    }

    def __init__(self, *args, **kw):
        super(JiraService, self).__init__(*args, **kw)
        self.username = self.config.get(self.target, 'jira.username')
        self.url = self.config.get(self.target, 'jira.base_uri')
        password = self.config.get(self.target, 'jira.password')
        if not password or password.startswith("@oracle:"):
            service = "jira://%s@%s" % (self.username, self.url)
            password = get_service_password(service, self.username,
                                            oracle=password,
                                            interactive=self.config.interactive)

        default_query = 'assignee=' + self.username + \
            ' AND status != closed and status != resolved'
        self.query = self.config.get(self.target, 'jira.query', default_query)
        self.project_prefix = self.config.get(
            self.target, 'jira.project_prefix', '')
        self.jira = JIRA(
            options={
                'server': self.config.get(self.target, 'jira.base_uri'),
                'rest_api_version': 'latest',
            },
            basic_auth=(self.username, password)
        )

    @classmethod
    def validate_config(cls, config, target):
        for option in ['jira.username', 'jira.password', 'jira.base_uri']:
            if not config.has_option(target, option):
                die("[%s] has no '%s'" % (target, option))

        IssueService.validate_config(config, target)

    def get_owner(self, issue):
        return True

    def annotations(self,  issue):

        annotations = []

        comments = self.jira.comments(issue)

        if comments is []:
            pass
        else:
            for comment in comments:
                created = date.fromtimestamp(time.mktime(time.strptime(
                    comment.created[0:10], '%Y-%m-%d')))

                annotations.append(self.format_annotation(
                    created, comment.author.name, comment.body))

        return dict(annotations)

    def __convert_for_jira4(self, issue):
        print(issue.key)

        class IssueWrapper:
            pass
        #print(self.jira.issue(issue.key).fields.summary.value)
        #print(self.jira.issue(issue.key).fields.summary)
        new_issue = self.jira.issue(issue.key)
        result = IssueWrapper()
        fields = IssueWrapper()
        fields.__dict__ = {
            'summary': new_issue.fields.summary.value,
            'priority': new_issue.fields.priority.name,
        }
        result.__dict__ = {
            'key': issue.key,
            'fields': fields,
        }
        return result

    def __issue(self, case, jira_version):
        result = dict(
            description=self.description(
                title=case.fields.summary,
                url=self.url + '/browse/' + case.key,
                number=case.key.rsplit('-', 1)[1],
                cls="issue"),
            project=self.project_prefix + case.key.rsplit('-', 1)[0],
            priority=self.priorities.get(
                get_priority(case.fields.priority),
                self.default_priority,
            )
        )
        if jira_version != 4:
            result.update(self.annotations(case.key))
        return result

    def issues(self):
        cases = self.jira.search_issues(self.query, maxResults=-1)

        jira_version = 5  # Default version number
        if self.config.has_option(self.target, 'jira.version'):
            jira_version = self.config.getint(self.target, 'jira.version')
        if jira_version == 4:
            # Convert for older jira versions that don't support the new API
            cases = [self.__convert_for_jira4(case) for case in cases]

        log.name(self.target).debug(" Found {0} total.", len(cases))
        return [self.__issue(case, jira_version) for case in cases]
