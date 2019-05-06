import bugzilla

import time
import pytz
import datetime
import six

from dateutil.parser import parse as parse_date
from dateutil.tz import tzlocal

from bugwarrior.config import die, asbool, aslist
from bugwarrior.services import IssueService, Issue

import logging
log = logging.getLogger(__name__)


class BugzillaIssue(Issue):
    URL = 'bugzillaurl'
    SUMMARY = 'bugzillasummary'
    BUG_ID = 'bugzillabugid'
    STATUS = 'bugzillastatus'
    NEEDINFO = 'bugzillaneedinfo'
    PRODUCT = 'bugzillaproduct'
    COMPONENT = 'bugzillacomponent'
    ASSIGNED_ON = 'bugzillaassignedon'

    UDAS = {
        URL: {
            'type': 'string',
            'label': 'Bugzilla URL',
        },
        SUMMARY: {
            'type': 'string',
            'label': 'Bugzilla Summary',
        },
        STATUS: {
            'type': 'string',
            'label': 'Bugzilla Status',
        },
        BUG_ID: {
            'type': 'numeric',
            'label': 'Bugzilla Bug ID',
        },
        NEEDINFO: {
            'type': 'date',
            'label': 'Bugzilla Needinfo',
        },
        PRODUCT: {
            'type': 'string',
            'label': 'Bugzilla Product',
        },
        COMPONENT: {
            'type': 'string',
            'label': 'Bugzilla Component',
        },
        ASSIGNED_ON: {
            'type': 'date',
            'label': 'Bugzilla Assigned On',
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
        task = {
            'project': self.record['component'],
            'priority': self.get_priority(),
            'annotations': self.extra.get('annotations', []),

            self.URL: self.extra['url'],
            self.SUMMARY: self.record['summary'],
            self.BUG_ID: self.record['id'],
            self.STATUS: self.record['status'],
            self.PRODUCT: self.record['product'],
            self.COMPONENT: self.record['component'],
        }
        if self.extra.get('needinfo_since', None) is not None:
            task[self.NEEDINFO] = self.extra.get('needinfo_since')

        # iff field is defined, use it, converting None to empty string.
        if 'assigned_on' in self.extra:
            task[self.ASSIGNED_ON] = self.extra.get('assigned_on') or ''

        return task

    def get_default_description(self):
        return self.build_default_description(
            title=self.record['summary'],
            url=self.get_processed_url(self.extra['url']),
            number=self.record['id'],
            cls='issue',
        )


_open_statuses = [
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


class BugzillaService(IssueService):
    ISSUE_CLASS = BugzillaIssue
    CONFIG_PREFIX = 'bugzilla'

    COLUMN_LIST = [
        'id',
        'status',
        'summary',
        'priority',
        'product',
        'component',
        'flags',
        'longdescs',
    ]

    def __init__(self, *args, **kw):
        super(BugzillaService, self).__init__(*args, **kw)
        self.base_uri = self.config.get('base_uri')
        self.username = self.config.get('username')
        self.ignore_cc = self.config.get('ignore_cc', default=False,
                                                 to_type=lambda x: x == "True")
        self.query_url = self.config.get('query_url', default=None)
        self.include_needinfos = self.config.get(
            'include_needinfos', False, to_type=lambda x: x == "True")
        self.open_statuses = self.config.get('open_statuses', _open_statuses, to_type=aslist)
        log.debug(" filtering on statuses: %r", self.open_statuses)

        # So more modern bugzilla's require that we specify
        # query_format=advanced along with the xmlrpc request.
        # https://bugzilla.redhat.com/show_bug.cgi?id=825370
        # ...but older bugzilla's don't know anything about that argument.
        # Here we make it possible for the user to specify whether they want
        # to pass that argument or not.
        self.advanced = asbool(self.config.get('advanced', 'no'))

        url = 'https://%s/xmlrpc.cgi' % self.base_uri
        api_key = self.config.get('api_key', default=None)
        if api_key:
            try:
                self.bz = bugzilla.Bugzilla(url=url, api_key=api_key)
            except TypeError:
                raise Exception("Bugzilla API keys require python-bugzilla>=2.1.0")
        else:
            password = self.get_password('password', self.username)
            self.bz = bugzilla.Bugzilla(url=url)
            self.bz.login(self.username, password)

    @staticmethod
    def get_keyring_service(service_config):
        username = service_config.get('username')
        base_uri = service_config.get('base_uri')
        return "bugzilla://%s@%s" % (username, base_uri)

    @classmethod
    def validate_config(cls, service_config, target):
        req = ['username', 'base_uri']
        for option in req:
            if option not in service_config:
                die("[%s] has no 'bugzilla.%s'" % (target, option))
        if 'password' not in service_config and 'api_key' not in service_config:
            die("[%s] has neither 'bugzilla.password' nor 'bugzilla.api_key'" % (target,))

        super(BugzillaService, cls).validate_config(service_config, target)

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
                bug_status=self.open_statuses,
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

        if self.include_needinfos:
            needinfos = self.bz.query(dict(
                column_list=self.COLUMN_LIST,
                quicksearch='flag:needinfo?%s' % email,
            ))
            exists = [b.id for b in bugs]
            for bug in needinfos:
                # don't double-add bugs that have already been found
                if bug.id in exists:
                    continue
                bugs.append(bug)

        # Convert to dicts
        bugs = [
            dict(
                ((col, _get_bug_attr(bug, col)) for col in self.COLUMN_LIST)
            ) for bug in bugs
        ]

        issues = [(self.target, bug) for bug in bugs]
        log.debug(" Found %i total.", len(issues))

        # Build a url for each issue
        base_url = "https://%s/show_bug.cgi?id=" % (self.base_uri)
        for tag, issue in issues:
            issue_obj = self.get_issue_for_record(issue)
            extra = {
                'url': base_url + six.text_type(issue['id']),
                'annotations': self.annotations(tag, issue, issue_obj),
            }

            needinfos = [f for f in issue['flags'] if (    f['name'] == 'needinfo'
                                          and f['status'] == '?'
                                          and f.get('requestee', self.username) == self.username)]
            if needinfos:
                last_mod = needinfos[0]['modification_date']
                # convert from RPC DateTime string to datetime.datetime object
                mod_date = datetime.datetime.fromtimestamp(
                    time.mktime(last_mod.timetuple()))

                extra['needinfo_since'] = pytz.UTC.localize(mod_date)

            if issue['status'] == 'ASSIGNED':
                extra['assigned_on'] = self._get_assigned_date(issue)
            else:
                extra['assigned_on'] = None

            issue_obj.update_extra(extra)
            yield issue_obj

    def _get_assigned_date(self, issue):
        assigned_date = None

        bug = self.bz.getbug(issue['id'])
        history = bug.get_history()['bugs'][0]['history']

        # this is already in chronological order, so the last change is the one we want
        h = history[-1]
        for change in h['changes']:
            if change['field_name'] == 'status' and change['added'] == 'ASSIGNED':
              assigned_date = h['when']

        # messy conversion :(
        # TODO: create method that's used here and in needinfos time conv above
        assigned_date_datetime = datetime.datetime.fromtimestamp(time.mktime(assigned_date.timetuple()))
        assigned_date_str = pytz.UTC.localize(assigned_date_datetime).isoformat()

        return assigned_date_str


def _get_bug_attr(bug, attr):
    """Default longdescs/flags case to [] since they may not be present."""
    if attr in ("longdescs", "flags"):
        return getattr(bug, attr, [])
    return getattr(bug, attr)
