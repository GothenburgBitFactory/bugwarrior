from collections.abc import Iterator
import datetime
import logging
import time
import typing
from typing import Annotated, Any
import urllib.parse
import xmlrpc.client

import bugzilla
import pydantic
from pydantic import BeforeValidator, Field

from bugwarrior import config
from bugwarrior.config.schema import StrippedTrailingSlashUrl
from bugwarrior.services import Issue, Service
from bugwarrior.task import IssueDatetime, Task, Udas

log = logging.getLogger(__name__)


def validate_url(value: str) -> str:
    if not urllib.parse.urlparse(value).scheme:
        value = f'https://{value}'
        log.warning(
            'Deprecation Warning: bugzilla.base_uri should include the '
            f'scheme ("{value}"). In a future version this will be an '
            'error.'
        )
    return value


OptionalSchemeUrl = Annotated[StrippedTrailingSlashUrl, BeforeValidator(validate_url)]


class BugzillaConfig(config.ServiceConfig):
    service: typing.Literal['bugzilla']
    KEYRING_SERVICE = "bugzilla://{username}@{base_uri}"
    username: str
    base_uri: OptionalSchemeUrl

    password: str = ''
    api_key: str = ''
    ignore_cc: bool = False
    open_statuses: config.ConfigList = [
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
    include_needinfos: bool = False
    query_url: typing.Optional[pydantic.AnyUrl] = None
    force_rest: bool = False
    advanced: bool = False


class BugzillaUdas(Udas):
    """Service-specific UDAs contributed by Bugzilla."""

    UNIQUE_KEY = ('bugzillaurl',)

    bugzillaurl: str = Field(title='Bugzilla URL')
    bugzillasummary: str = Field(title='Bugzilla Summary')
    bugzillastatus: str = Field(title='Bugzilla Status')
    bugzillabugid: int = Field(title='Bugzilla Bug ID')
    bugzillaneedinfo: IssueDatetime = Field(title='Bugzilla Needinfo')
    bugzillaproduct: str = Field(title='Bugzilla Product')
    bugzillacomponent: str = Field(title='Bugzilla Component')
    bugzillaassignedon: IssueDatetime = Field(title='Bugzilla Assigned On')


class BugzillaTask(Task):
    udas: BugzillaUdas


class BugzillaIssue(Issue):
    PRIORITY_MAP = {
        'unspecified': 'M',
        'low': 'L',
        'medium': 'M',
        'high': 'H',
        'urgent': 'H',
    }

    def to_taskwarrior(self) -> BugzillaTask:
        return BugzillaTask(
            project=self.record['component'],
            priority=self.get_priority(),
            annotations=self.extra.get('annotations', []),
            udas=BugzillaUdas(
                bugzillaurl=self.extra['url'],
                bugzillasummary=self.record['summary'],
                bugzillabugid=self.record['id'],
                bugzillastatus=self.record['status'],
                bugzillaproduct=self.record['product'],
                bugzillacomponent=self.record['component'],
                bugzillaneedinfo=self.extra.get('needinfo_since'),
                bugzillaassignedon=self.extra.get('assigned_on'),
            ),
        )

    def get_default_description(self) -> str:
        return self.build_default_description(
            title=self.record['summary'],
            url=self.extra['url'],
            number=self.record['id'],
            cls='issue',
        )


class BugzillaService(Service):
    API_VERSION = 2.0
    ISSUE_CLASS = BugzillaIssue
    TASK_SCHEMA = BugzillaTask
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

    def __init__(
        self, config: BugzillaConfig, main_config: config.MainSectionConfig
    ) -> None:
        super().__init__(config, main_config)
        log.debug(" filtering on statuses: %r", self.config.open_statuses)

        force_rest_kwargs = {}
        if self.config.force_rest:
            force_rest_kwargs = {"force_rest": True}

        if self.config.api_key:
            api_key = self.get_secret('api_key')
            try:
                self.bz = bugzilla.Bugzilla(
                    url=self.config.base_uri, api_key=api_key, **force_rest_kwargs
                )
            except TypeError:
                raise Exception("Bugzilla API keys require python-bugzilla>=2.1.0")
        else:
            self.bz = bugzilla.Bugzilla(url=self.config.base_uri, **force_rest_kwargs)
            if self.config.password:
                password = self.get_secret('password', self.config.username)
                self.bz.login(self.config.username, password)

    def get_owner(self, issue: dict[str, Any]) -> str:
        return issue['assigned_to']

    def include(self, issue: dict[str, Any]) -> bool:
        """Return true if the issue in question should be included"""
        if self.config.only_if_assigned:
            owner = self.get_owner(issue)
            include_owners: list[str | None] = [self.config.only_if_assigned]

            if self.config.also_unassigned:
                include_owners.append(None)

            return owner in include_owners

        return True

    def annotations(self, tag: str, issue: dict[str, Any]) -> list[str]:
        base_url = "%s/show_bug.cgi?id=" % self.config.base_uri
        long_url = base_url + str(issue['id'])
        url = long_url

        if 'comments' in issue:
            comments = issue.get('comments', [])
            return self.build_annotations(
                ((c['author'].split('@')[0], c['text']) for c in comments), url
            )
        else:
            # Backwards compatibility (old python-bugzilla/bugzilla instances)
            # This block handles a million different contingencies that have to
            # do with different version of python-bugzilla and different
            # version of bugzilla itself.  :(
            comments = issue.get('longdescs', [])

            def _parse_author(obj: dict[str, Any] | str) -> str:
                if isinstance(obj, dict):
                    return obj['login_name'].split('@')[0]
                else:
                    return obj

            def _parse_body(obj: dict[str, Any]) -> str | None:
                return obj.get('text', obj.get('body'))

            return self.build_annotations(
                ((_parse_author(c['author']), _parse_body(c) or "") for c in comments),
                url,
            )

    def issues(self) -> Iterator[Task]:
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
            needinfos = self.bz.query(
                dict(
                    column_list=self.COLUMN_LIST, quicksearch='flag:needinfo?%s' % email
                )
            )
            exists = [b.id for b in bugs]
            for bug in needinfos:
                # don't double-add bugs that have already been found
                if bug.id in exists:
                    continue
                bugs.append(bug)

        # Convert to dicts
        bugs = [
            {col: _get_bug_attr(bug, col) for col in self.COLUMN_LIST} for bug in bugs
        ]

        bugs = filter(self.include, bugs)
        issues = [(self.config.target, bug) for bug in bugs]
        log.debug(" Found %i total.", len(issues))

        # Build a url for each issue
        base_url = "%s/show_bug.cgi?id=" % self.config.base_uri
        for tag, issue in issues:
            extra = {
                'url': base_url + str(issue['id']),
                'annotations': self.annotations(tag, issue),
            }

            username = self.config.username
            needinfos = [
                f
                for f in issue['flags']
                if (
                    f['name'] == 'needinfo'
                    and f['status'] == '?'
                    and f.get('requestee', username) == username
                )
            ]
            if needinfos:
                last_mod = needinfos[0]['modification_date']
                extra['needinfo_since'] = _ensure_datetime(last_mod).isoformat()

            if issue['status'] == 'ASSIGNED':
                extra['assigned_on'] = self._get_assigned_date(issue)
            else:
                extra['assigned_on'] = None

            yield self.process_record(issue, extra)

    def _get_assigned_date(self, issue: dict[str, Any]) -> str | None:
        bug = self.bz.getbug(issue['id'])
        history = bug.get_history_raw()['bugs'][0]['history']

        # this is already in chronological order, so the last change is the one we want
        for h in reversed(history):
            for change in h['changes']:
                if change['field_name'] == 'status' and change['added'] == 'ASSIGNED':
                    return _ensure_datetime(h['when']).isoformat()


def _get_bug_attr(bug: Any, attr: str) -> Any:
    """Default longdescs/flags case to [] since they may not be present."""
    if attr in ("longdescs", "flags"):
        return getattr(bug, attr, [])
    return getattr(bug, attr)


def _ensure_datetime(
    timestamp: typing.Union[datetime.datetime, str, xmlrpc.client.DateTime],
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
        return datetime.datetime.fromtimestamp(structured, tz=datetime.timezone.utc)
    else:
        raise TypeError(
            "Timestamp conversion from `{0!r}` is not supported.".format(timestamp)
        )
