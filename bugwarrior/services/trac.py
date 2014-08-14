import offtrac
from twiggy import log

from bugwarrior.config import die, get_service_password
from bugwarrior.services import Issue, IssueService


class TracIssue(Issue):
    SUMMARY = 'tracsummary'
    URL = 'tracurl'
    NUMBER = 'tracnumber'

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
        }

    def get_default_description(self):
        return self.build_default_description(
            title=self.record['summary'],
            url=self.get_processed_url(self.record['url']),
            number=self.record['number'],
            cls='issue'
        )

    def get_priority(self):
        return self.PRIORITY_MAP.get(
            self.record.get('priority'),
            self.origin['default_priority']
        )


class TracService(IssueService):
    ISSUE_CLASS = TracIssue
    CONFIG_PREFIX = 'trac'

    def __init__(self, *args, **kw):
        super(TracService, self).__init__(*args, **kw)
        base_uri = self.config_get('base_uri')
        username = self.config_get('username')
        password = self.config_get('password')
        if not password or password.startswith('@oracle:'):
            service = "https://%s@%s/" % (username, base_uri)
            password = get_service_password(
                service, username, oracle=password,
                interactive=self.config.interactive
            )

        uri = 'https://%s:%s@%s/login/xmlrpc' % (username, password, base_uri)
        self.trac = offtrac.TracServer(uri)

    @classmethod
    def validate_config(cls, config, target):
        for option in ['trac.username', 'trac.password', 'trac.base_uri']:
            if not config.has_option(target, option):
                die("[%s] has no '%s'" % (target, option))

        IssueService.validate_config(config, target)

    def annotations(self, tag, issue):
        annotations = []
        changelog = self.trac.server.ticket.changeLog(issue['number'])
        for time, author, field, oldvalue, newvalue, permament in changelog:
            if field == 'comment':
                annotations.append((author, newvalue, ))

        url = issue['url']
        url = self.get_issue_for_record(issue).get_processed_url(url)
        return self.build_annotations(annotations, url)

    def get_owner(self, issue):
        tag, issue = issue
        return issue.get('owner', None) or None

    def issues(self):
        base_url = "https://" + self.config.get(self.target, 'trac.base_uri')
        tickets = self.trac.query_tickets('status!=closed&max=0')
        tickets = map(self.trac.get_ticket, tickets)
        issues = [(self.target, ticket[3]) for ticket in tickets]
        log.name(self.target).debug(" Found {0} total.", len(issues))

        # Build a url for each issue
        for i in range(len(issues)):
            issues[i][1]['url'] = "%s/ticket/%i" % (base_url, tickets[i][0])
            issues[i][1]['number'] = tickets[i][0]

        issues = filter(self.include, issues)
        log.name(self.target).debug(" Pruned down to {0}", len(issues))

        for project, issue in issues:
            extra = {
                'annotations': self.annotations(project, issue),
                'project': project,
            }
            yield self.get_issue_for_record(issue, extra)
