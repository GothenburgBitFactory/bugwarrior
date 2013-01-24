from __future__ import absolute_import

import time
from datetime import date

from twiggy import log
from jira.client import JIRA

from bugwarrior.services import IssueService
from bugwarrior.config import die

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
        self.query = 'assignee=' + self.username + ' AND status != closed and status != resolved'
        self.jira = JIRA(options={'server': self.config.get(self.target, 'jira.base_uri')},
                         basic_auth=(self.username,
                                     self.config.get(self.target, 'jira.password')))

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
                created = date.fromtimestamp(time.mktime(time.strptime(comment.created[0:10], '%Y-%m-%d')))

                annotations.append(self.format_annotation(created, comment.author.name, comment.body))

        return dict(annotations)

    def issues(self):
        cases = self.jira.search_issues(self.query, maxResults=-1)

        log.debug(" Found {0} total.", len(cases))

        return [dict(
            description=self.description(
                title=case.fields.summary,
                url=self.url + '/browse/' + case.key,
                number=case.key.rsplit('-', 1)[1], cls="issue",
            ),
            project=case.key.rsplit('-', 1)[0],
            priority=self.priorities.get(
                get_priority(case.fields.priority),
                self.default_priority,
            ),
            **self.annotations(case.key)
        ) for case in cases]
