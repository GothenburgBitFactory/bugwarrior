from builtins import str
import six

from bugwarrior.config import aslist
from bugwarrior.services import IssueService, Issue

# This comes from PyPI
import phabricator

import logging
log = logging.getLogger(__name__)


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

        self.shown_user_phids = (
            self.config.get("user_phids", None, aslist))

        self.shown_project_phids = (
            self.config.get("project_phids", None, aslist))

    def issues(self):

        # TODO -- get a list of these from the api
        projects = {}
        # If self.shown_user_phids or self.shown_project_phids is set, retrict API calls to user_phids or project_phids
        # to avoid time out with Phabricator installations with huge userbase
        if (self.shown_user_phids is not None) or (self.shown_project_phids is not None):
            if self.shown_user_phids is not None:
                issues_owner = self.api.maniphest.query(status='status-open', ownerPHIDs=self.shown_user_phids)
                issues_cc = self.api.maniphest.query(status='status-open', ccPHIDs=self.shown_user_phids)
                issues_author = self.api.maniphest.query(status='status-open', authorPHIDs=self.shown_user_phids)
                issues = list(issues_owner.items()) + list(issues_cc.items()) + list(issues_author.items())
                # Delete duplicates
                seen = set()
                issues = [item for item in issues if str(item[1]) not in seen and not seen.add(str(item[1]))]
            if self.shown_project_phids is not None:
                issues = self.api.maniphest.query(status='status-open', projectsPHIDs = self.shown_project_phids)
                issues = issues.items()
        else:
            issues = self.api.maniphest.query(status='status-open')
            issues = issues.items()

        log.info("Found %i issues" % len(issues))

        for phid, issue in issues:

            project = self.target  # a sensible default
            try:
                project = projects.get(issue['projectPHIDs'][0], project)
            except IndexError:
                pass

            this_issue_matches = False

            if self.shown_user_phids is None and self.shown_project_phids is None:
                this_issue_matches = True

            if self.shown_user_phids is not None:
                # Checking whether authorPHID, ccPHIDs, ownerPHID
                # are intersecting with self.shown_user_phids
                issue_relevant_to = set(issue['ccPHIDs'] + [issue['ownerPHID'], issue['authorPHID']])
                if len(issue_relevant_to.intersection(self.shown_user_phids)) > 0:
                    this_issue_matches = True

            if self.shown_project_phids is not None:
                # Checking whether projectPHIDs
                # is intersecting with self.shown_project_phids
                issue_relevant_to = set(issue['projectPHIDs'])
                if len(issue_relevant_to.intersection(self.shown_user_phids)) > 0:
                    this_issue_matches = True

            if not this_issue_matches:
                continue

            extra = {
                'project': project,
                'type': 'issue',
                #'annotations': self.annotations(phid, issue)
            }

            yield self.get_issue_for_record(issue, extra)

        diffs = self.api.differential.query(status='status-open')
        diffs = list(diffs)

        log.info("Found %i differentials" % len(diffs))

        for diff in diffs:

            project = self.target  # a sensible default
            try:
                project = projects.get(issue['projectPHIDs'][0], project)
            except IndexError:
                pass

            this_diff_matches = False

            if self.shown_user_phids is None and self.shown_project_phids is None:
                this_diff_matches = True

            if self.shown_user_phids is not None:
                # Checking whether authorPHID, ccPHIDs, ownerPHID
                # are intersecting with self.shown_user_phids
                diff_relevant_to = set(list(diff['reviewers']) + [diff['authorPHID']])
                if len(diff_relevant_to.intersection(self.shown_user_phids)) > 0:
                    this_diff_matches = True

            if self.shown_project_phids is not None:
                # Checking whether projectPHIDs
                # is intersecting with self.shown_project_phids
                phabricator_projects = []
                try:
                    phabricator_projects = diff['phabricator:projects']
                except KeyError:
                    pass

                diff_relevant_to = set(phabricator_projects + [diff['repositoryPHID']])
                if len(diff_relevant_to.intersection(self.shown_user_phids)) > 0:
                    this_diff_matches = True

            if not this_diff_matches:
                continue

            extra = {
                'project': project,
                'type': 'pull_request',
                #'annotations': self.annotations(phid, issue)
            }
            yield self.get_issue_for_record(diff, extra)
