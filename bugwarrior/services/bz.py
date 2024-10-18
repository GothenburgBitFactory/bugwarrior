import datetime
import logging
import urllib.parse
import time
import typing
import xmlrpc.client

import bugzilla
import pydantic.v1
import pytz
import typing_extensions

from bugwarrior import config
from bugwarrior.services import Service, Issue

log = logging.getLogger(__name__)


class OptionalSchemeUrl(pydantic.v1.AnyUrl):
    """
    A temporary type to use during the deprecation period of scheme-less urls.
    """

    @classmethod
    def validate(cls, value, field, config):
        if not urllib.parse.urlparse(value).scheme:
            value = f'https://{value}'
            log.warning(
                'Deprecation Warning: bugzilla.base_uri should include the '
                f'scheme ("{value}"). In a future version this will be an '
                'error.'
            )
        return super().validate(value.rstrip('/'), field, config)


class BugzillaConfig(config.ServiceConfig):
    service: typing_extensions.Literal['bugzilla']
    username: str
    base_uri: OptionalSchemeUrl

    password: str = ''
    api_key: str = ''
    ignore_cc: bool = False
    open_statuses: config.ConfigList = config.ConfigList([
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
    ])
    include_needinfos: bool = False
    query_url: typing.Optional[pydantic.v1.AnyUrl]
    force_rest: bool = False
    advanced: bool = False


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
            task[self.NEEDINFO] = self.parse_date(self.extra.get('needinfo_since'))

        if self.extra.get('assigned_on', None) is not None:
            task[self.ASSIGNED_ON] = self.parse_date(self.extra.get('assigned_on'))

        return task

    def get_default_description(self):
        return self.build_default_description(
            title=self.record['summary'],
            url=self.extra['url'],
            number=self.record['id'],
            cls='issue',
        )


class BugzillaService(Service):
    ISSUE_CLASS = BugzillaIssue
    CONFIG_SCHEMA = BugzillaConfig

    COLUMN_LIST = [
        'id',
        'status',
        'summary',
        'priority',
        'product',
        'component',
        'flags',
        'longdescs',
        'assigned_to',
    ]

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        log.debug(" filtering on statuses: %r", self.config.open_statuses)

        force_rest_kwargs = {}
        if self.config.force_rest:
            force_rest_kwargs = {"force_rest": True}

        if self.config.api_key:
            api_key = self.get_password('api_key')
            try:
                self.bz = bugzilla.Bugzilla(url=self.config.base_uri,
                                            api_key=api_key,
                                            **force_rest_kwargs)
            except TypeError:
                raise Exception("Bugzilla API keys require python-bugzilla>=2.1.0")
        else:
            self.bz = bugzilla.Bugzilla(url=self.config.base_uri,
                                        **force_rest_kwargs)
            if self.config.password:
                password = self.get_password('password', self.config.username)
                self.bz.login(self.config.username, password)

    @staticmethod
    def get_keyring_service(config):
        return f"bugzilla://{config.username}@{config.base_uri}"

    def get_owner(self, issue):
        return issue['assigned_to']

    def include(self, issue):
        """ Return true if the issue in question should be included """
        if self.config.only_if_assigned:
            owner = self.get_owner(issue)
            include_owners = [self.config.only_if_assigned]

            if self.config.also_unassigned:
                include_owners.append(None)

            return owner in include_owners

        return True

    def annotations(self, tag, issue):
        base_url = "%s/show_bug.cgi?id=" % self.config.base_uri
        long_url = base_url + str(issue['id'])
        url = long_url

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
        email = self.config.username
        # TODO -- doing something with blockedby would be nice.

        if self.config.query_url:
            query = self.bz.url_to_query(self.config.query_url)
            query['column_list'] = self.COLUMN_LIST
        else:
            query = dict(
                column_list=self.COLUMN_LIST,
                bug_status=self.config.open_statuses,
                email1=email,
                emailreporter1=1,
                emailassigned_to1=1,
                emailqa_contact1=1,
                emailtype1="substring",
            )

            if not self.config.ignore_cc:
                query['emailcc1'] = 1

        if self.config.advanced:
            # Required for new bugzilla
            # https://bugzilla.redhat.com/show_bug.cgi?id=825370
            query['query_format'] = 'advanced'

        bugs = self.bz.query(query)

        if self.config.include_needinfos:
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
            {
                col: _get_bug_attr(bug, col) for col in self.COLUMN_LIST
            } for bug in bugs
        ]

        bugs = filter(self.include, bugs)
        issues = [(self.config.target, bug) for bug in bugs]
        log.debug(" Found %i total.", len(issues))

        # Build a url for each issue
        base_url = "%s/show_bug.cgi?id=" % self.config.base_uri
        for tag, issue in issues:
            issue_obj = self.get_issue_for_record(issue)
            extra = {
                'url': base_url + str(issue['id']),
                'annotations': self.annotations(tag, issue),
            }

            username = self.config.username
            needinfos = [f for f in issue['flags'] if (
                f['name'] == 'needinfo' and
                f['status'] == '?' and
                f.get('requestee', username) == username
            )]
            if needinfos:
                last_mod = needinfos[0]['modification_date']
                extra['needinfo_since'] = _ensure_datetime(last_mod).isoformat()

            if issue['status'] == 'ASSIGNED':
                extra['assigned_on'] = self._get_assigned_date(issue)
            else:
                extra['assigned_on'] = None

            issue_obj.extra.update(extra)
            yield issue_obj

    def _get_assigned_date(self, issue):
        bug = self.bz.getbug(issue['id'])
        history = bug.get_history_raw()['bugs'][0]['history']

        # this is already in chronological order, so the last change is the one we want
        for h in reversed(history):
            for change in h['changes']:
                if change['field_name'] == 'status' and change['added'] == 'ASSIGNED':
                    return _ensure_datetime(h['when']).isoformat()


def _get_bug_attr(bug, attr):
    """Default longdescs/flags case to [] since they may not be present."""
    if attr in ("longdescs", "flags"):
        return getattr(bug, attr, [])
    return getattr(bug, attr)


def _ensure_datetime(
    timestamp: typing.Union[
        datetime.datetime,
        str,
        xmlrpc.client.DateTime,
    ],
) -> datetime.datetime:
    """Convert "timestamp" into native `datetime.datetime` object.

    Arguments:
        timestamp: The source time data.
            * `datetime.datetime`: No-op.
            * `str`: Assumed to be ISO8601 string timestamp and parsed as such.
            * `xmlrpc.client.DateTime`: Lacks timezone info. Assuming this is in UTC.

    Returns:
        Native equivalent of the source date and time.
    """

    if isinstance(timestamp, datetime.datetime):
        return timestamp
    elif isinstance(timestamp, str):
        return datetime.datetime.fromisoformat(timestamp)
    elif isinstance(timestamp, xmlrpc.client.DateTime):
        structured = time.mktime(timestamp.timetuple())
        naive = datetime.datetime.fromtimestamp(structured)
        return pytz.UTC.localize(naive)
    else:
        raise TypeError("Timestamp conversion from `{0!r}` is not supported.".format(timestamp))
