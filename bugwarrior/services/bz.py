from twiggy import log

import bugzilla

from bugwarrior.services import IssueService
from bugwarrior.config import die


class BugzillaService(IssueService):
    priorities = {
        'unspecified': 'M',
        'low': 'L',
        'medium': 'M',
        'high': 'H',
        'urgent': 'H',
    }
    not_closed_statuses = [
        'NEW',
        'ASSIGNED',
        'NEEDINFO',
        'ON_DEV',
        'MODIFIED',
        'POST',
        'REOPENED',
        'ON_QA',
        'FAILS_QA',
        'PASSES_QA',
    ]
    column_list = [
        'id',
        'summary',
        'priority',
        'component'
    ]

    def __init__(self, *args, **kw):
        super(BugzillaService, self).__init__(*args, **kw)
        url = 'https://%s/xmlrpc.cgi' % \
                self.config.get(self.target, 'bugzilla.base_uri')
        self.bz = bugzilla.Bugzilla(url=url)
        self.bz.login(
            self.config.get(self.target, 'bugzilla.username'),
            self.config.get(self.target, 'bugzilla.password'),
        )

    @classmethod
    def validate_config(cls, config, target):
        req = ['bugzilla.username', 'bugzilla.password', 'bugzilla.base_uri']
        for option in req:
            if not config.has_option(target, option):
                die("[%s] has no '%s'" % (target, option))

        IssueService.validate_config(config, target)

    def get_owner(self, issue):
        # NotImplemented, but we should never get called since .include() isn't
        # used by this IssueService.
        raise NotImplementedError

    def issues(self):
        email = self.config.get(self.target, 'bugzilla.username')
        # TODO -- doing something with blockedby would be nice.

        query = dict(
            column_list=self.column_list,
            bug_status=self.not_closed_statuses,
            email1=email,
            emailreporter1=1,
            emailcc1=1,
            emailassigned_to1=1,
            emailqa_contact1=1,
            emailtype1="substring",
            # Required for new bugzilla
            # https://bugzilla.redhat.com/show_bug.cgi?id=825370
            query_format='advanced',
        )
        bugs = self.bz.query(query)


        # Convert to dicts
        bugs = [
            dict(
                ((col, getattr(bug, col)) for col in self.column_list)
            ) for bug in bugs
        ]

        issues = [(self.target, bug) for bug in bugs]
        log.debug(" Found {0} total.", len(issues))

        # Build a url for each issue
        base_url = "https://%s/show_bug.cgi?id=" % \
                self.config.get(self.target, 'bugzilla.base_uri')
        for i in range(len(issues)):
            issues[i][1]['url'] = base_url + str(issues[i][1]['id'])
            issues[i][1]['component'] = \
                    issues[i][1]['component'].lower().replace(' ', '-')

        # XXX - Note that we don't use the .include() method like all the other
        # IssueService child classes.  That's because the bugzilla xmlrpc API
        # can already do a lot of the filtering we want for us.

        #issues = filter(self.include, issues)
        #log.debug(" Pruned down to {0}", len(issues))

        return [{
            "description": self.description(
                issue['summary'], issue['url'],
                issue['id'], cls="issue",
            ),
            "project": issue['component'],
            "priority": self.priorities.get(
                issue['priority'],
                self.default_priority,
            ),
        } for tag, issue in issues]
