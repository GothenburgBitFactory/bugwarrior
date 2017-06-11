from builtins import str
import re

from jinja2 import Template
import six

from bugwarrior.config import aslist, asbool
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
            'tags': self.get_tags(),

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

    def _normalize_to_tag(self, s):
        return re.sub(r'[^a-zA-Z0-9]', '_', s)

    def get_tags(self):
        tags = []

        if not self.origin['should_set_tags']:
            return tags

        projects = self.extra['projects']

        template = Template(self.origin['tag_template'])
        for p in projects:
            slug = p['fields']['slug']
            slug = self.apply_tag_substitutions(slug)
            context = self.record.copy()
            context.update({
                'project_slug': self._normalize_to_tag(slug),
            })
            rendered = template.render(context)
            tags.append(rendered)
        return tags

    def apply_tag_substitutions(self, tag):
        """Applies a user's regexes and replacement strings to a tag

        :self: Gets from self a list of substitutions with form ['find#replace', 'findme#replacewithme', ...]
        :returns: A function that takes a tag and returns another tag
        """
        exprs = self.origin['tag_substitutions']
        if len(exprs) == 0:
            return tag
        exprs = [e.split('#', 1) for e in exprs]
        def reducer(acc, upd):
            [pattern, sub] = upd
            return re.sub(pattern, sub, acc)
        return reduce(reducer, exprs, tag)


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

        self.should_set_tags = self.config.get(
            'should_set_tags', default=False, to_type=asbool
        )
        self.tag_substitutions = self.config.get(
            'tag_substitutions', default=[], to_type=aslist
        )
        self.tag_template = self.config.get(
            'tag_template', default='{{project_slug}}', to_type=six.text_type
        )

    def get_service_metadata(self):
        return {
            'should_set_tags': self.should_set_tags,
            'tag_template': self.tag_template,
            'tag_substitutions': self.tag_substitutions,
        }

    def issues(self):

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

        projects = fetch_issue_metadata(self.api, issues)

        for phid, issue in issues:

            # TODO fix this now that we have access to proper projects.
            # It was bugged before
            project = self.target

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
                'projects': get_projects_of_issue(issue, projects),
                'type': 'issue',
                #'annotations': self.annotations(phid, issue)
            }

            yield self.get_issue_for_record(issue, extra)

        diffs = self.api.differential.query(status='status-open')
        diffs = list(diffs)

        log.info("Found %i differentials" % len(diffs))

        diff_metadata = fetch_diff_metadata(self.api, diffs)

        for diff in diffs:

            # TODO fix this now that we have access to proper projects.
            # It was bugged before
            project = self.target  # a sensible default

            projects_from_repo = diff_metadata['repo_binds'][diff['repositoryPHID']]

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

                phabricator_projects += projects_from_repo

                # TODO The docs say project PHIDs decide relevancy, but here a
                # repository PHID is used instead
                diff_relevant_to = set(phabricator_projects + [diff['repositoryPHID']])
                if len(diff_relevant_to.intersection(self.shown_user_phids)) > 0:
                    this_diff_matches = True

            if not this_diff_matches:
                continue

            extra = {
                'project': project,
                'projects': [diff_metadata['projects'][p_phid] for p_phid in projects_from_repo],
                'type': 'pull_request',
                #'annotations': self.annotations(phid, issue)
            }
            yield self.get_issue_for_record(diff, extra)

def fetch_issue_metadata(api, issues):
    """Get projects related to a list of issues from Phab

    :api: Phabricator api object
    :issues: A list of phab issue tuples with form (issue_phid, issue)
    :returns: A dictionary with form {project_phid: project_data}
    """
    proj_phid_lists = [i[1]['projectPHIDs'] for i in issues]
    return fetch_all_related_projects(api, proj_phid_lists)

def fetch_diff_metadata(api, diffs):
    """Get repo and projects related to a list of issues from Phab

    :api: Phabricator api object
    :diffs: A list of phab diffs
    :returns: A dictionary with form {
        'repo_binds': {repo_phid: [project_phid, ...]},
        'projects': {project_phid: project_data}
    }
    """
    repo_phids = [d['repositoryPHID'] for d in diffs]
    repo_phids = [p for p in set(repo_phids)] # make unique

    # We could try to also use the diff['auxiliary']['phabricator:projects']
    # here, which the diff relevancy filtering code tries to do,
    # but I haven't seen this information actually be set in any real
    # calls to the phab conduit API

    repos = api.diffusion.repository.search(
        constraints={'phids': repo_phids},
        attachments={'projects': True}
    )

    repo_proj_phid = {}
    for r in repos.data:
        repo_phid = r['phid']
        att = r.get('attachments', None)
        if att is None:
            repo_proj_phid[repo_phid] = None
            continue
        proj_att = att.get('projects', None)
        if proj_att is None:
            repo_proj_phid[repo_phid] = None
            continue
        repo_proj_phid[repo_phid] = proj_att.get('projectPHIDs', None)

    projects = fetch_all_related_projects(api, repo_proj_phid.values())

    return {
        'repo_binds': repo_proj_phid,
        'projects': projects
    }

def fetch_all_related_projects(api, proj_phid_lists):
    phids = set()
    for pl in proj_phid_lists:
        if pl is None:
            continue
        for phid in pl:
            phids.add(phid)

    phids = [p for p in phids] # set to list
    projs = api.project.search(constraints={'phids': phids})

    resdict = {}
    for p in projs.data:
        resdict[p['phid']] = p
    return resdict

def get_projects_of_issue(issue, projects):
    """Get projects related to an issue from a dict of Phab projects

    :issue: Issue which we want to get related projects of
    :returns: A list of related projects
    """
    proj_phids = issue.get('projectPHIDs', None)
    if proj_phids is None:
        return []

    return [projects[phid] for phid in proj_phids]
