import debianbts
import requests

from bugwarrior.config import die
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

            self.URL: self.record['url'],
            self.SUBJECT: self.record['subject'],
            self.NUMBER: self.record['number'],
            self.PACKAGE: self.record['package'],
            self.SOURCE: self.record['source'],
            self.FORWARDED: self.record['forwarded'],
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
            self.record.get('priority'),
            self.origin['default_priority']
        )


class BTSService(IssueService, ServiceClient):
    ISSUE_CLASS = BTSIssue
    CONFIG_PREFIX = 'bts'

    def __init__(self, *args, **kw):
        super(BTSService, self).__init__(*args, **kw)
        self.email = self.config_get_default('email', default=None)
        self.packages = self.config_get_default('packages', default=None)
        self.udd = self.config_get_default('udd', default=False).lower() in ['true', 'yes', 'enabled']
        self.udd_ignore_sponsor = self.config_get_default('udd_ignore_sponsor', default="True").lower() in ['true', 'yes', 'enabled']
        self.ignore_pkg = self.config_get_default('ignore_pkg', default=None)
        self.ignore_src = self.config_get_default('ignore_src', default=None)

    @classmethod
    def validate_config(cls, config, target):
#        if not config.has_option(target, 'trac.base_uri'):
#            die("[%s] has no 'base_uri'" % target)
#        elif '://' in config.get(target, 'trac.base_uri'):
#            die("[%s] do not include scheme in 'base_uri'" % target)

        IssueService.validate_config(config, target)

    def _issue_from_bug(self, bug):
        return {'number': bug.bug_num,
                'url': 'https://bugs.debian.org/' + str(bug.bug_num),
                'package': bug.package,
                'subject': bug.subject,
                'severity': bug.severity,
                'source': bug.source,
                'forwarded': bug.forwarded,
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

    def issues(self):
        # Initialise empty list of bug numbers
        collected_bugs = []

        # Search BTS for bugs owned by email address
        if self.email:
            owned_bugs = debianbts.get_bugs("owner", self.email, "status", "open")
            collected_bugs.extend(owned_bugs)

        # Search BTS for bugs related to specified packages
        if self.packages:
            packages = self.packages.split(",")
            for pkg in packages:
                pkg_bugs = debianbts.get_bugs("package", pkg, "status", "open")
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

        issues = [self._issue_from_bug(bug) for bug in debianbts.get_status(collected_bugs)]

        log.debug(" Found %i total.", len(issues))

        if self.ignore_pkg:
            ignore_pkg = self.ignore_pkg.split(",")
            for pkg in ignore_pkg:
                issues = [issue for issue in issues if not issue['package'] == pkg]

        if self.ignore_src:
            ignore_src = self.ignore_src.split(",")
            for src in ignore_src:
                issues = [issue for issue in issues if not issue['source'] == src]

        log.debug(" Pruned down to %i.", len(issues))

        for issue in issues:
            issue_obj = self.get_issue_for_record(issue)
            yield issue_obj

