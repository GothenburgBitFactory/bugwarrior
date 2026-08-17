from collections.abc import Iterable, Iterator
import logging
import typing
from typing import Any

import debianbts
import pydantic
from pydantic import Field, model_validator
import requests

from bugwarrior import config
from bugwarrior.config import Priority
from bugwarrior.services import Client, Issue, Service
from bugwarrior.task import Task, Udas

log = logging.getLogger(__name__)

UDD_BUGS_SEARCH = "https://udd.debian.org/bugs/"


class BTSConfig(config.ServiceConfig):
    service: typing.Literal['bts']
    KEYRING_SERVICE = 'bts://'

    email: pydantic.EmailStr = ''
    packages: config.ConfigList = []

    udd: bool = False
    ignore_pending: bool = True
    udd_ignore_sponsor: bool = True
    ignore_pkg: config.ConfigList = []
    ignore_src: config.ConfigList = []

    only_if_assigned: config.UnsupportedOption[str] = ''
    also_unassigned: config.UnsupportedOption[bool] = False

    @model_validator(mode='after')
    def require_email_or_packages(self) -> "BTSConfig":
        if not self.email and not self.packages:
            raise ValueError('section requires one of:\n    email\n    packages')
        return self

    @model_validator(mode='after')
    def udd_needs_email(self) -> "BTSConfig":
        if self.udd and not self.email:
            raise ValueError("no 'email' but UDD search was requested")
        return self


class BTSUdas(Udas):
    """Service-specific UDAs contributed by the Debian BTS."""

    UNIQUE_KEY = ('btsurl',)

    btssubject: str = Field(title='Debian BTS Subject')
    btsurl: str = Field(title='Debian BTS URL')
    btsnumber: int = Field(title='Debian BTS Number')
    btspackage: str = Field(title='Debian BTS Package')
    btssource: str = Field(title='Debian BTS Source Package')
    btsforwarded: str = Field(title='Debian BTS Forwarded URL')
    btsstatus: str = Field(title='Debian BTS Status')


class BTSTask(Task):
    udas: BTSUdas


class BTSIssue(Issue):
    PRIORITY_MAP: dict[str, Priority] = {
        'wishlist': 'L',
        'minor': 'L',
        'normal': 'M',
        'important': 'M',
        'serious': 'H',
        'grave': 'H',
        'critical': 'H',
    }

    def to_taskwarrior(self) -> BTSTask:
        return BTSTask(
            priority=self.get_priority(),
            annotations=self.extra.get('annotations', []),
            udas=BTSUdas(
                btssubject=self.record['subject'],
                btsurl=self.record['url'],
                btsnumber=self.record['number'],
                btspackage=self.record['package'],
                btssource=self.record['source'],
                btsforwarded=self.record['forwarded'],
                btsstatus=self.record['status'],
            ),
        )

    def get_default_description(self) -> str:
        return self.build_default_description(
            title=self.record['subject'],
            url=self.record['url'],
            number=self.record['number'],
            cls='issue',
        )

    def get_priority(self) -> config.Priority:
        return self.PRIORITY_MAP.get(
            self.record.get('severity', ''), self.config.default_priority
        )


class BTSService(Service):
    API_VERSION = 2.0
    ISSUE_CLASS = BTSIssue
    TASK_SCHEMA = BTSTask
    CONFIG_SCHEMA = BTSConfig

    def _record_for_bug(self, bug: debianbts.Bugreport) -> dict[str, Any]:
        return {
            'number': bug.bug_num,
            'url': 'https://bugs.debian.org/' + str(bug.bug_num),
            'package': bug.package,
            'subject': bug.subject,
            'severity': bug.severity,
            'source': bug.source,
            'forwarded': bug.forwarded,
            'status': bug.pending,
        }

    def _get_udd_bugs(self) -> Iterable[dict[str, Any]]:
        request_params = {'format': 'json', 'dmd': 1, 'email1': self.config.email}
        if self.config.udd_ignore_sponsor:
            request_params['nosponsor1'] = "on"
        resp = requests.get(UDD_BUGS_SEARCH, request_params)
        return Client.json_response(resp)

    def annotations(self, issue: dict[str, Any]) -> list[str]:
        return self.build_annotations([], issue['url'])

    def issues(self) -> Iterator[Task]:
        # Initialise empty list of bug numbers
        collected_bugs = []

        # Search BTS for bugs owned by email address
        if self.config.email:
            owned_bugs = debianbts.get_bugs(owner=self.config.email, status="open")
            collected_bugs.extend(owned_bugs)

        # Search BTS for bugs related to specified packages
        for pkg in self.config.packages:
            pkg_bugs = debianbts.get_bugs(package=pkg, status="open")
            for bug in pkg_bugs:
                if bug not in collected_bugs:
                    collected_bugs.append(bug)

        # Search UDD bugs search for bugs belonging to packages that
        # are maintained by the email address
        if self.config.udd:
            udd_bugs = self._get_udd_bugs()
            for bug in udd_bugs:
                if bug not in collected_bugs:
                    collected_bugs.append(bug['id'])

        issues = [
            self._record_for_bug(bug) for bug in debianbts.get_status(collected_bugs)
        ]

        log.debug(" Found %i total.", len(issues))

        for pkg in self.config.ignore_pkg:
            issues = [issue for issue in issues if not issue['package'] == pkg]

        for src in self.config.ignore_src:
            issues = [issue for issue in issues if not issue['source'] == src]

        if self.config.ignore_pending:
            issues = [
                issue for issue in issues if not issue['status'] == 'pending-fixed'
            ]

        issues = [
            issue
            for issue in issues
            if not (issue['status'] == 'done' or issue['status'] == 'fixed')
        ]

        log.debug(" Pruned down to %i.", len(issues))

        for issue in issues:
            extra = {'annotations': self.annotations(issue)}
            yield self.process_record(issue, extra)
