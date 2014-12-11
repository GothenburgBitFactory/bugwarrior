import bugzilla
from twiggy import log

import six

from bugwarrior.config import die, asbool, get_service_password
from bugwarrior.services import IssueService, Issue


class BugzillaIssue(Issue):
    URL = 'bugzillaurl'
    SUMMARY = 'bugzillasummary'
    BUG_ID = 'bugzillabugid'

    UDAS = {
        URL: {
            'type': 'string',
            'label': 'Bugzilla URL',
        },
        SUMMARY: {
            'type': 'string',
            'label': 'Bugzilla Summary',
        },
        BUG_ID: {
            'type': 'numeric',
            'label': 'Bugzilla Bug ID',
        },
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
            'annotations': self.extra.get('annotations', []),

            self.URL: self.extra['url'],
            self.SUMMARY: self.record['summary'],
            self.BUG_ID: self.record['id'],
        }

    def get_default_description(self):
        return self.build_default_description(
            title=self.record['summary'],
            url=self.get_processed_url(self.extra['url']),
            number=self.record['id'],
            cls='issue',
        )


class BugzillaService(IssueService):
    ISSUE_CLASS = BugzillaIssue
    CONFIG_PREFIX = 'bugzilla'

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
        self.base_uri = self.config_get('base_uri')
        self.username = self.config_get('username')
        self.password = self.config_get('password')
        self.ignore_cc = self.config_get_default('ignore_cc', default=False,
                                                 to_type=lambda x: x == "True")
        self.query_url = self.config_get_default('query_url', default=None)

        # So more modern bugzilla's require that we specify
        # query_format=advanced along with the xmlrpc request.
        # https://bugzilla.redhat.com/show_bug.cgi?id=825370
        # ...but older bugzilla's don't know anything about that argument.
        # Here we make it possible for the user to specify whether they want
        # to pass that argument or not.
        self.advanced = asbool(self.config_get_default('advanced', 'no'))

        if not self.password or self.password.startswith("@oracle:"):
            self.password = get_service_password(
                self.get_keyring_service(self.config, self.target),
                self.username, oracle=self.password,
                interactive=self.config.interactive
            )

        url = 'https://%s/xmlrpc.cgi' % self.base_uri
        self.bz = bugzilla.Bugzilla(url=url)
        self.bz.login(self.username, self.password)

    @classmethod
    def get_keyring_service(cls, config, section):
        username = config.get(section, cls._get_key('username'))
        base_uri = config.get(section, cls._get_key('base_uri'))
        return "bugzilla://%s@%s" % (username, base_uri)

    @classmethod
    def validate_config(cls, config, target):
        req = ['bugzilla.username', 'bugzilla.password', 'bugzilla.base_uri']
        for option in req:
            if not config.has_option(target, option):
                die("[%s] has no '%s'" % (target, option))

        super(BugzillaService, cls).validate_config(config, target)

    def get_owner(self, issue):
        # NotImplemented, but we should never get called since .include() isn't
        # used by this IssueService.
        raise NotImplementedError

    def annotations(self, tag, issue, issue_obj):
        base_url = "https://%s/show_bug.cgi?id=" % self.base_uri
        long_url = base_url + six.text_type(issue['id'])
        url = issue_obj.get_processed_url(long_url)

        if 'comments' in issue:
            comments = issue.get('comments', [])
            return self.build_annotations(
                ((
                    c['author'].split('@')[0],
                    c['text'],
                ) for c in comments),
                url
            )
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

            return self.build_annotations(
                ((
                    _parse_author(c['author']),
                    _parse_body(c)
                ) for c in comments),
                url
            )

    def issues(self):
        email = self.username
        # TODO -- doing something with blockedby would be nice.

        if self.query_url:
            query = self.bz.url_to_query(self.query_url)
            query['column_list'] = self.COLUMN_LIST
        else:
            query = dict(
                column_list=self.COLUMN_LIST,
                bug_status=self.OPEN_STATUSES,
                email1=email,
                emailreporter1=1,
                emailassigned_to1=1,
                emailqa_contact1=1,
                emailtype1="substring",
            )

            if not self.ignore_cc:
                query['emailcc1'] = 1

        if self.advanced:
            # Required for new bugzilla
            # https://bugzilla.redhat.com/show_bug.cgi?id=825370
            query['query_format'] = 'advanced'

        bugs = self.bz.query(query)
        # Convert to dicts
        bugs = [
            dict(
                ((col, _get_bug_attr(bug, col)) for col in self.COLUMN_LIST)
            ) for bug in bugs
        ]

        issues = [(self.target, bug) for bug in bugs]
        log.name(self.target).debug(" Found {0} total.", len(issues))

        # Build a url for each issue
        base_url = "https://%s/show_bug.cgi?id=" % (self.base_uri)
        for tag, issue in issues:
            issue_obj = self.get_issue_for_record(issue)
            extra = {
                'url': base_url + six.text_type(issue['id']),
                'annotations': self.annotations(tag, issue, issue_obj),
            }
            issue_obj.update_extra(extra)
            yield issue_obj


def _get_bug_attr(bug, attr):
    """Default only the longdescs case to [] since it may not be present."""
    if attr == "longdescs":
        return getattr(bug, attr, [])
    return getattr(bug, attr)
