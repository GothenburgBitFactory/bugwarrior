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

    PRIORITY_MAP = {
        'Needs Triage': None,
        'Unbreak Now!': 'H',
        'High': 'H',
        'Normal': 'M',
        'Low': 'L',
        'Wishlist': 'L',
    }

    def to_taskwarrior(self):
        return {
            'project': self.extra['project'],
            'priority': self.priority,
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

    @property
    def priority(self):
        return self.PRIORITY_MAP.get(self.record.get('priority')) \
               or self.origin['default_priority']


class PhabricatorService(IssueService):
    ISSUE_CLASS = PhabricatorIssue
    CONFIG_PREFIX = 'phabricator'

    def __init__(self, *args, **kw):
        super(PhabricatorService, self).__init__(*args, **kw)

        self.host = self.config.get("host", None)

        # These read login credentials from ~/.arcrc
        if self.host is not None:
            self.api = phabricator.Phabricator(host=self.host)
        else:
            self.api = phabricator.Phabricator()

        self.shown_user_phids = (
            self.config.get("user_phids", None, aslist))

        self.shown_project_phids = (
            self.config.get("project_phids", None, aslist))

        self.ignore_cc = self.config.get('ignore_cc', default=False,
                                          to_type=lambda x: x == "True")

        self.ignore_author = self.config.get('ignore_author', default=False,
                                             to_type=lambda x: x == "True")

        self.ignore_owner = self.config.get('ignore_owner', default=False,
                                             to_type=lambda x: x == "True")

        self.ignore_reviewers = self.config.get('ignore_reviewers', default=False,
                                                to_type=lambda x: x == "True")

    def tasks(self):
        # If self.shown_user_phids or self.shown_project_phids is set, retrict API calls to user_phids or project_phids
        # to avoid time out with Phabricator installations with huge userbase
        try:
            if (self.shown_user_phids is not None) or (self.shown_project_phids is not None):
                if self.shown_user_phids is not None:
                    tasks_owner = self.api.maniphest.query(status='status-open', ownerPHIDs=self.shown_user_phids)
                    tasks_cc = self.api.maniphest.query(status='status-open', ccPHIDs=self.shown_user_phids)
                    tasks_author = self.api.maniphest.query(status='status-open', authorPHIDs=self.shown_user_phids)
                    tasks = list(tasks_owner.items()) + list(tasks_cc.items()) + list(tasks_author.items())
                    # Delete duplicates
                    seen = set()
                    tasks = [item for item in tasks if str(item[1]) not in seen and not seen.add(str(item[1]))]
                if self.shown_project_phids is not None:
                    tasks = self.api.maniphest.query(status='status-open', projectPHIDs=self.shown_project_phids)
                    tasks = tasks.items()
            else:
                tasks = self.api.maniphest.query(status='status-open')
                tasks = tasks.items()
        except phabricator.APIError as err:
            log.warn("Could not read tasks from Maniphest: %s" % err)
            return

        log.info("Found %i tasks" % len(tasks))

        for phid, task in tasks:

            project = self.target  # a sensible default

            this_task_matches = False

            if self.shown_user_phids is None and self.shown_project_phids is None:
                this_task_matches = True

            if self.shown_user_phids is not None:
                # Checking whether authorPHID, ccPHIDs, ownerPHID
                # are intersecting with self.shown_user_phids
                task_relevant_to = set()
                if not self.ignore_cc:
                    task_relevant_to.update(task['ccPHIDs'])
                if not self.ignore_owner:
                    task_relevant_to.add(task['ownerPHID'])
                if not self.ignore_author:
                    task_relevant_to.add(task['authorPHID'])
                if len(task_relevant_to.intersection(self.shown_user_phids)) > 0:
                    this_task_matches = True

            if self.shown_project_phids is not None:
                # Checking whether projectPHIDs
                # is intersecting with self.shown_project_phids
                task_relevant_to = set(task['projectPHIDs'])
                if len(task_relevant_to.intersection(self.shown_project_phids)) > 0:
                    this_task_matches = True

            if not this_task_matches:
                continue

            extra = {
                'project': project,
                'type': 'issue',
                #'annotations': self.annotations(phid, issue)
            }

            yield self.get_issue_for_record(issue, extra)

    def revisions(self):
        try:
            diffs = self.api.differential.query(status='status-open')
        except phabricator.APIError as err:
            log.warn("Could not read revisions from Differential: %s" % err)
            return

        diffs = list(diffs)

        log.info("Found %i differentials" % len(diffs))

        for diff in diffs:

            project = self.target  # a sensible default

            this_diff_matches = False

            if self.shown_user_phids is None and self.shown_project_phids is None:
                this_diff_matches = True

            if self.shown_user_phids is not None:
                # Checking whether authorPHID, ccPHIDs, reviewers
                # are intersecting with self.shown_user_phids
                diff_relevant_to = set()
                if not self.ignore_reviewers:
                    diff_relevant_to.update(list(diff['reviewers']))
                if not self.ignore_cc:
                    diff_relevant_to.update(diff['ccs'])
                if not self.ignore_author:
                    diff_relevant_to.add(diff['authorPHID'])
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
                if len(diff_relevant_to.intersection(self.shown_project_phids)) > 0:
                    this_diff_matches = True

            if not this_diff_matches:
                continue

            extra = {
                'project': project,
                'type': 'pull_request',
                #'annotations': self.annotations(phid, issue)
            }
            yield self.get_issue_for_record(diff, extra)

    def issues(self):
        for issue in self.tasks():
            yield issue
        for issue in self.revisions():
            yield issue
