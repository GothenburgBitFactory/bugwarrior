from twiggy import log

import bugzilla

from bugwarrior.services import IssueService
from bugwarrior.config import die, asbool, get_service_password

import datetime
import time


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
            password = get_service_password(service, username, oracle=password,
                                            interactive=self.config.interactive)

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
            return dict([
                self.format_annotation(
                    datetime.datetime.fromtimestamp(time.mktime(time.strptime(
                        c['time'].value, "%Y%m%dT%H:%M:%S"))),
                    c['author'].split('@')[0],
                    c['text'],
                ) for c in comments])
        else:
            # Backwards compatibility (old python-bugzilla/bugzilla instances)
            comments = issue.get('longdescs', [])
            return dict([
                self.format_annotation(
                    datetime.datetime.fromtimestamp(time.mktime(time.strptime(
                        c['time'], "%Y-%m-%d %H:%M:%S"))),
                    c['author']['login_name'].split('@')[0],
                    c['body'],
                ) for c in issue['longdescs']])

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
        )

        if self.advanced:
            # Required for new bugzilla
            # https://bugzilla.redhat.com/show_bug.cgi?id=825370
            query['query_format'] = 'advanced'

        bugs = self.bz.query(query)

        # Convert to dicts
        bugs = [
            dict(
                ((col, getattr(bug, col)) for col in self.column_list)
            ) for bug in bugs
        ]

        issues = [(self.target, bug) for bug in bugs]
        log.name(self.target).debug(" Found {0} total.", len(issues))

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
        #log.name(self.target).debug(" Pruned down to {0}", len(issues))

        return [dict(
            description=self.description(
                issue['summary'], issue['url'],
                issue['id'], cls="issue"),
            project=issue['component'],
            priority=self.priorities.get(
                issue['priority'],
                self.default_priority,
            ),
            **self.annotations(tag, issue)
        ) for tag, issue in issues]
