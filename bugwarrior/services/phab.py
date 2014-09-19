import six
from twiggy import log

from bugwarrior.services import IssueService, Issue

# This comes from PyPI
import phabricator


class PhabricatorIssue(Issue):
    TITLE = 'phabricatortitle'
    URL = 'phabricatorurl'
    TYPE = 'phabricatortype'
    OBJECT_NAME = 'phabricatorid'

    UDAS = {
        TITLE: {
            'type': 'string',
            'label': 'Phabricator Title',
        },
        URL: {
            'type': 'string',
            'label': 'Phabricator URL',
        },
        TYPE: {
            'type': 'string',
            'label': 'Phabricator Type',
        },
        OBJECT_NAME: {
            'type': 'string',
            'label': 'Phabricator Object',
        },
    }
    UNIQUE_KEY = (URL, )

    def to_taskwarrior(self):
        return {
            'project': self.extra['project'],
            'priority': self.origin['default_priority'],
            'annotations': self.extra.get('annotations', []),

            self.URL: self.record['uri'],
            self.TYPE: self.extra['type'],
            self.TITLE: self.record['title'],
            self.OBJECT_NAME: self.record['uri'].split('/')[-1],
        }

    def get_default_description(self):
        return self.build_default_description(
            title=self.record['title'],
            url=self.get_processed_url(self.record['uri']),
            number=self.record['uri'].split('/')[-1],
            cls=self.extra['type'],
        )


class PhabricatorService(IssueService):
    ISSUE_CLASS = PhabricatorIssue
    CONFIG_PREFIX = 'phabricator'

    def __init__(self, *args, **kw):
        super(PhabricatorService, self).__init__(*args, **kw)
        # These reads in login credentials from ~/.arcrc
        self.api = phabricator.Phabricator()

    def issues(self):

        # TODO -- get a list of these from the api
        projects = {}

        issues = self.api.maniphest.query(status='status-open')
        issues = list(issues.iteritems())

        log.name(self.target).info("Found %i issues" % len(issues))

        for phid, issue in issues:
            project = self.target  # a sensible default
            try:
                project = projects.get(issue['projectPHIDs'][0], project)
            except IndexError:
                pass

            extra = {
                'project': project,
                'type': 'issue',
                #'annotations': self.annotations(phid, issue)
            }
            yield self.get_issue_for_record(issue, extra)

        diffs = self.api.differential.query(status='status-open')
        diffs = list(diffs)

        log.name(self.target).info("Found %i differentials" % len(diffs))

        for diff in list(diffs):
            project = self.target  # a sensible default
            try:
                project = projects.get(issue['projectPHIDs'][0], project)
            except IndexError:
                pass

            extra = {
                'project': project,
                'type': 'pull_request',
                #'annotations': self.annotations(phid, issue)
            }
            yield self.get_issue_for_record(diff, extra)
