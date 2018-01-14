from builtins import str
import debianbts
import requests

from bugwarrior.config import die, asbool
from bugwarrior.services import Issue, IssueService, ServiceClient

import logging
log = logging.getLogger(__name__)

UDD_BUGS_SEARCH = "https://udd.debian.org/bugs/"


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
            url=self.get_processed_url(self.record['url']),
            number=self.record['number'],
            cls='issue'
        )

    def get_priority(self):
        return self.PRIORITY_MAP.get(
            self.record.get('severity'),
            self.origin['default_priority']
        )


class BTSService(IssueService, ServiceClient):
    ISSUE_CLASS = BTSIssue
    CONFIG_PREFIX = 'bts'

    def __init__(self, *args, **kw):
        super(BTSService, self).__init__(*args, **kw)
        self.email = self.config.get('email', default=None)
        self.packages = self.config.get('packages', default=None)
        self.udd = self.config.get(
            'udd', default=False, to_type=asbool)
        self.udd_ignore_sponsor = self.config.get(
            'udd_ignore_sponsor', default=True, to_type=asbool)
        self.ignore_pkg = self.config.get('ignore_pkg', default=None)
        self.ignore_src = self.config.get('ignore_src', default=None)
        self.ignore_pending = self.config.get(
            'ignore_pending', default=True, to_type=asbool)

    @classmethod
    def validate_config(cls, service_config, target):
        if ('udd' in service_config and
                asbool(service_config.get('udd')) and
                'email' not in service_config):
            die("[%s] has no 'bts.email' but UDD search was requested" %
                (target,))

        if 'packages' not in service_config and 'email' not in service_config:
            die("[%s] has neither 'bts.email' or 'bts.packages'" % (target,))

        if ('udd_ignore_sponsor' in service_config and
            (not asbool(service_config.get('udd')))):
            die("[%s] defines settings for UDD search without enabling"
                " UDD search" % (target,))

        IssueService.validate_config(service_config, target)

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
            'email1': self.email,
            }
        if self.udd_ignore_sponsor:
            request_params['nosponsor1'] = "on"
        resp = requests.get(UDD_BUGS_SEARCH, request_params)
        return self.json_response(resp)

    def annotations(self, issue, issue_obj):
        return self.build_annotations(
            [],
            issue_obj.get_processed_url(issue['url'])
        )

    def issues(self):
        # Initialise empty list of bug numbers
        collected_bugs = []

        # Search BTS for bugs owned by email address
        if self.email:
            owned_bugs = debianbts.get_bugs("owner", self.email,
                                            "status", "open")
            collected_bugs.extend(owned_bugs)

        # Search BTS for bugs related to specified packages
        if self.packages:
            packages = self.packages.split(",")
            for pkg in packages:
                pkg_bugs = debianbts.get_bugs("package", pkg,
                                              "status", "open")
                for bug in pkg_bugs:
                    if bug not in collected_bugs:
                        collected_bugs.append(bug)

        # Search UDD bugs search for bugs belonging to packages that
        # are maintained by the email address
        if self.udd:
            udd_bugs = self._get_udd_bugs()
            for bug in udd_bugs:
                if bug not in collected_bugs:
                    collected_bugs.append(bug['id'])

        issues = [self._record_for_bug(bug)
                  for bug in debianbts.get_status(collected_bugs)]

        log.debug(" Found %i total.", len(issues))

        if self.ignore_pkg:
            ignore_pkg = self.ignore_pkg.split(",")
            for pkg in ignore_pkg:
                issues = [issue
                          for issue in issues if not issue['package'] == pkg]

        if self.ignore_src:
            ignore_src = self.ignore_src.split(",")
            for src in ignore_src:
                issues = [issue
                          for issue in issues if not issue['source'] == src]

        if self.ignore_pending:
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
                'annotations': self.annotations(issue, issue_obj)
            }
            issue_obj.update_extra(extra)
            yield issue_obj
