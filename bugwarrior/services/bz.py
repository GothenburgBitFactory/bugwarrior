import bugzilla
from twiggy import log

from bugwarrior.config import die, asbool, get_service_password
from bugwarrior.services import IssueService, Issue


class BugzillaIssue(Issue):
    URL = 'bugzilla_url'
    SUMMARY = 'bugzilla_summary'

    UDAS = {
        URL: {
            'type': 'string',
            'label': 'Bugzilla URL',
        },
        SUMMARY: {
            'type': 'string',
            'label': 'Bugzilla Summary',
        }
    }
    UNIQUE_KEY = (URL, )

    PRIORITY_MAP = {
        'unspecified': 'M',
        'low': 'L',
        'medium': 'M',
        'high': 'H',
        'urgent': 'H',
    }

    def to_taskwarrior(self):
        return {
            'project': self.record['component'],
            'priority': self.get_priority(),
            'annotations': self.record['annotations'],

            self.URL: self.extra['url'],
            self.SUMMARY: self.record['summary'],
        }

    def get_default_description(self):
        return self.build_default_description(
            title=self.record['summary'],
            url=self.extra['url'],
            number=self.record['id'],
            cls='issue',
        )


class BugzillaService(IssueService):
    ISSUE_CLASS = BugzillaIssue

    OPEN_STATUSES = [
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
    COLUMN_LIST = [
        'id',
        'summary',
        'priority',
        'component',
        'longdescs',
    ]

    def __init__(self, *args, **kw):
        super(BugzillaService, self).__init__(*args, **kw)
        base_uri = self.config.get(self.target, 'bugzilla.base_uri')
        username = self.config.get(self.target, 'bugzilla.username')
        password = self.config.get(self.target, 'bugzilla.password')

        # So more modern bugzilla's require that we specify
        # query_format=advanced along with the xmlrpc request.
        # https://bugzilla.redhat.com/show_bug.cgi?id=825370
        # ...but older bugzilla's don't know anything about that argument.
        # Here we make it possible for the user to specify whether they want
        # to pass that argument or not.
        self.advanced = True  # Default to True.
        if self.config.has_option(self.target, 'bugzilla.advanced'):
            self.advanced = asbool(self.config.get(
                self.target, 'bugzilla.advanced'))

        if not password or password.startswith("@oracle:"):
            service = "bugzilla://%s@%s" % (username, base_uri)
            password = get_service_password(
                service, username, oracle=password,
                interactive=self.config.interactive
            )

        url = 'https://%s/xmlrpc.cgi' % base_uri
        self.bz = bugzilla.Bugzilla(url=url)
        self.bz.login(username, password)

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

    def annotations(self, tag, issue):
        if 'comments' in issue:
            comments = issue.get('comments', [])
            return [
                '%s: %s' % (
                    c['author'].split('@')[0],
                    c['text'],
                ) for c in comments
            ]
        else:
            # Backwards compatibility (old python-bugzilla/bugzilla instances)
            # This block handles a million different contingencies that have to
            # do with different version of python-bugzilla and different
            # version of bugzilla itself.  :(
            comments = issue.get('longdescs', [])

            def _parse_author(obj):
                if isinstance(obj, dict):
                    return obj['login_name'].split('@')[0]
                else:
                    return obj

            def _parse_body(obj):
                return obj.get('text', obj.get('body'))

            return [
                '%s: %s' % (
                    _parse_author(c['author']),
                    _parse_body(c)
                ) for c in issue['longdescs']
            ]

    def issues(self):
        email = self.config.get(self.target, 'bugzilla.username')
        # TODO -- doing something with blockedby would be nice.

        query = dict(
            column_list=self.COLUMN_LIST,
            bug_status=self.OPEN_STATUSES,
            email1=email,
            emailreporter1=1,
            emailcc1=1,
            emailassigned_to1=1,
            emailqa_contact1=1,
            emailtype1="substring",
        )

        if self.advanced:
            # Required for new bugzilla
            # https://bugzilla.redhat.com/show_bug.cgi?id=825370
            query['query_format'] = 'advanced'

        bugs = self.bz.query(query)

        # Convert to dicts
        bugs = [
            dict(
                ((col, getattr(bug, col)) for col in self.COLUMN_LIST)
            ) for bug in bugs
        ]

        issues = [(self.target, bug) for bug in bugs]
        log.name(self.target).debug(" Found {0} total.", len(issues))

        # Build a url for each issue
        base_url = "https://%s/show_bug.cgi?id=" % (
            self.config.get(self.target, 'bugzilla.base_uri')
        )
        for issue in issues:
            extra = {
                'url': base_url + str(issue['id'])
            }
            yield self.get_issue_for_record(issue, extra)
