import sys

import pydantic.v1
import requests
import typing_extensions

from bugwarrior import config
from bugwarrior.services import Issue, Service, ServiceClient

import logging
log = logging.getLogger(__name__)

try:
    import debianbts
except AttributeError as e:
    # Suppress exception if we're just building docs in python-3.11+.
    if 'sphinx' not in ''.join(sys.argv):
        log.warning('debianbts does not support python-3.11+')
        raise e

UDD_BUGS_SEARCH = "https://udd.debian.org/bugs/"


class BTSConfig(config.ServiceConfig):
    service: typing_extensions.Literal['bts']

    email: pydantic.v1.EmailStr = pydantic.v1.EmailStr('')
    packages: config.ConfigList = config.ConfigList([])

    udd: bool = False
    ignore_pending: bool = True
    udd_ignore_sponsor: bool = True
    ignore_pkg: config.ConfigList = config.ConfigList([])
    ignore_src: config.ConfigList = config.ConfigList([])

    @pydantic.v1.root_validator
    def require_email_or_packages(cls, values):
        if not values['email'] and not values['packages']:
            raise ValueError(
                'section requires one of:\n    email\n    packages')
        return values

    @pydantic.v1.root_validator
    def udd_needs_email(cls, values):
        if values['udd'] and not values['email']:
            raise ValueError("no 'email' but UDD search was requested")
        return values

    @pydantic.v1.root_validator
    def python_version_limited(cls, values):
        log.warning(
            'The Debian BTS service has a dependency that has not yet been '
            'ported to python-3.11+. If this has not been resolved by October '
            '2026, when python-3.10 hits EOL, this service is liable to be '
            'removed. See '
            '<https://github.com/venthur/python-debianbts/issues/59>.')
        return values


class BTSIssue(Issue):
    SUBJECT = 'btssubject'
    URL = 'btsurl'
    NUMBER = 'btsnumber'
    PACKAGE = 'btspackage'
    SOURCE = 'btssource'
    FORWARDED = 'btsforwarded'
    STATUS = 'btsstatus'

    UDAS = {
        SUBJECT: {
            'type': 'string',
            'label': 'Debian BTS Subject',
        },
        URL: {
            'type': 'string',
            'label': 'Debian BTS URL',
        },
        NUMBER: {
            'type': 'numeric',
            'label': 'Debian BTS Number',
        },
        PACKAGE: {
            'type': 'string',
            'label': 'Debian BTS Package',
        },
        SOURCE: {
            'type': 'string',
            'label': 'Debian BTS Source Package',
        },
        FORWARDED: {
            'type': 'string',
            'label': 'Debian BTS Forwarded URL',
        },
        STATUS: {
            'type': 'string',
            'label': 'Debian BTS Status',
        }
    }
    UNIQUE_KEY = (URL, )

    PRIORITY_MAP = {
        'wishlist': 'L',
        'minor': 'L',
        'normal': 'M',
        'important': 'M',
        'serious': 'H',
        'grave': 'H',
        'critical': 'H',
    }

    def to_taskwarrior(self):
        return {
            'priority': self.get_priority(),
            'annotations': self.extra.get('annotations', []),

            self.URL: self.record['url'],
            self.SUBJECT: self.record['subject'],
            self.NUMBER: self.record['number'],
            self.PACKAGE: self.record['package'],
            self.SOURCE: self.record['source'],
            self.FORWARDED: self.record['forwarded'],
            self.STATUS: self.record['status'],
        }

    def get_default_description(self):

        return self.build_default_description(
            title=self.record['subject'],
            url=self.record['url'],
            number=self.record['number'],
            cls='issue'
        )

    def get_priority(self):
        return self.PRIORITY_MAP.get(
            self.record.get('severity'),
            self.config.default_priority
        )


class BTSService(Service, ServiceClient):
    ISSUE_CLASS = BTSIssue
    CONFIG_SCHEMA = BTSConfig

    def get_owner(self, issue):
        # TODO
        raise NotImplementedError(
            "This service has not implemented support for 'only_if_assigned'.")

    def _record_for_bug(self, bug):
        return {'number': bug.bug_num,
                'url': 'https://bugs.debian.org/' + str(bug.bug_num),
                'package': bug.package,
                'subject': bug.subject,
                'severity': bug.severity,
                'source': bug.source,
                'forwarded': bug.forwarded,
                'status': bug.pending,
                }

    def _get_udd_bugs(self):
        request_params = {
            'format': 'json',
            'dmd': 1,
            'email1': self.config.email,
        }
        if self.config.udd_ignore_sponsor:
            request_params['nosponsor1'] = "on"
        resp = requests.get(UDD_BUGS_SEARCH, request_params)
        return self.json_response(resp)

    def annotations(self, issue):
        return self.build_annotations(
            [],
            issue['url']
        )

    def issues(self):
        # Initialise empty list of bug numbers
        collected_bugs = []

        # Search BTS for bugs owned by email address
        if self.config.email:
            owned_bugs = debianbts.get_bugs(owner=self.config.email,
                                            status="open")
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

        issues = [self._record_for_bug(bug)
                  for bug in debianbts.get_status(collected_bugs)]

        log.debug(" Found %i total.", len(issues))

        for pkg in self.config.ignore_pkg:
            issues = [issue for issue in issues if not issue['package'] == pkg]

        for src in self.config.ignore_src:
            issues = [issue for issue in issues if not issue['source'] == src]

        if self.config.ignore_pending:
            issues = [issue
                      for issue in issues
                      if not issue['status'] == 'pending-fixed']

        issues = [issue
                  for issue in issues
                  if not (issue['status'] == 'done' or
                          issue['status'] == 'fixed')]

        log.debug(" Pruned down to %i.", len(issues))

        for issue in issues:
            issue_obj = self.get_issue_for_record(issue)
            extra = {
                'annotations': self.annotations(issue)
            }
            issue_obj.extra.update(extra)
            yield issue_obj
