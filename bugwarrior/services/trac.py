from twiggy import log

import offtrac

from bugwarrior.services import IssueService
from bugwarrior.config import die


class TracService(IssueService):
    # A map of bitbucket priorities to taskwarrior priorities
    priorities = {
        'trivial': 'L',
        'minor': 'L',
        'major': 'M',
        'critical': 'H',
        'blocker': 'H',
    }

    def __init__(self, *args, **kw):
        super(TracService, self).__init__(*args, **kw)
        uri = 'https://%s:%s@%s/login/xmlrpc' % (
            self.config.get(self.target, 'trac.username'),
            self.config.get(self.target, 'trac.password'),
            self.config.get(self.target, 'trac.base_uri'),
        )
        self.trac = offtrac.TracServer(uri)

    @classmethod
    def validate_config(cls, config, target):
        for option in ['trac.username', 'trac.password', 'trac.base_uri']:
            if not config.has_option(target, option):
                die("[%s] has no '%s'" % (target, option))

        IssueService.validate_config(config, target)

    def get_owner(self, issue):
        tag, issue = issue
        return issue.get('owner', None) or None

    def issues(self):
        base_url = "https://" + self.config.get(self.target, 'trac.base_uri')
        tickets = self.trac.query_tickets('status!=closed')
        tickets = map(self.trac.get_ticket, tickets)
        issues = [(self.target, ticket[3]) for ticket in tickets]
        log.debug(" Found {0} total.", len(issues))

        # Build a url for each issue
        for i in range(len(issues)):
            issues[i][1]['url'] = "%s/ticket/%i" % (base_url, tickets[i][0])
            issues[i][1]['number'] = tickets[i][0]

        issues = filter(self.include, issues)
        log.debug(" Pruned down to {0}", len(issues))

        return [{
            "description": self.description(
                issue['summary'], issue['url'],
                issue['number'], cls="issue",
            ),
            "project": tag,
            "priority": self.priorities.get(issue['priority'], 'M'),
        } for tag, issue in issues]
