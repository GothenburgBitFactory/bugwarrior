from builtins import filter
import re
import six
import datetime
import pytz

import requests

from jinja2 import Template

from bugwarrior.config import asbool, aslist, die
from bugwarrior.services import IssueService, Issue

import logging
log = logging.getLogger(__name__)


class PagureIssue(Issue):
    TITLE = 'paguretitle'
    DATE_CREATED = 'paguredatecreated'
    URL = 'pagureurl'
    REPO = 'pagurerepo'
    TYPE = 'paguretype'
    ID = 'pagureid'

    UDAS = {
        TITLE: {
            'type': 'string',
            'label': 'Pagure Title',
        },
        DATE_CREATED: {
            'type': 'date',
            'label': 'Pagure Created',
        },
        REPO: {
            'type': 'string',
            'label': 'Pagure Repo Slug',
        },
        URL: {
            'type': 'string',
            'label': 'Pagure URL',
        },
        TYPE: {
            'type': 'string',
            'label': 'Pagure Type',
        },
        ID: {
            'type': 'numeric',
            'label': 'Pagure Issue/PR #',
        },
    }
    UNIQUE_KEY = (URL, TYPE,)

    def _normalize_label_to_tag(self, label):
        return re.sub(r'[^a-zA-Z0-9]', '_', label)

    def to_taskwarrior(self):
        if self.extra['type'] == 'pull_request':
            priority = 'H'
        else:
            priority = self.origin['default_priority']

        return {
            'project': self.extra['project'],
            'priority': priority,
            'annotations': self.extra.get('annotations', []),
            'tags': self.get_tags(),

            self.URL: self.record['html_url'],
            self.REPO: self.record['repo'],
            self.TYPE: self.extra['type'],
            self.TITLE: self.record['title'],
            self.ID: self.record['id'],
            self.DATE_CREATED: datetime.datetime.fromtimestamp(
                int(self.record['date_created']), pytz.UTC),
        }

    def get_tags(self):
        tags = []

        if not self.origin['import_tags']:
            return tags

        context = self.record.copy()
        tag_template = Template(self.origin['tag_template'])

        for tagname in self.record.get('tags', []):
            context.update({'label': self._normalize_label_to_tag(tagname) })
            tags.append(tag_template.render(context))

        return tags

    def get_default_description(self):
        return self.build_default_description(
            title=self.record['title'],
            url=self.get_processed_url(self.record['html_url']),
            number=self.record['id'],
            cls=self.extra['type'],
        )


class PagureService(IssueService):
    ISSUE_CLASS = PagureIssue
    CONFIG_PREFIX = 'pagure'

    def __init__(self, *args, **kw):
        super(PagureService, self).__init__(*args, **kw)

        self.session = requests.Session()

        self.tag = self.config.get('tag')
        self.repo = self.config.get('repo')
        self.base_url = self.config.get('base_url')

        self.exclude_repos = self.config.get('exclude_repos', [], aslist)
        self.include_repos = self.config.get('include_repos', [], aslist)

        self.import_tags = self.config.get(
            'import_tags', default=False, to_type=asbool
        )
        self.tag_template = self.config.get(
            'tag_template', default='{{label}}', to_type=six.text_type
        )

    def get_service_metadata(self):
        return {
            'import_tags': self.import_tags,
            'tag_template': self.tag_template,
        }

    def get_issues(self, repo, keys):
        """ Grab all the issues """
        key1, key2 = keys
        key3 = key1[:-1]  # Just the singular form of key1

        url = self.base_url + "/api/0/" + repo + "/" + key1
        response = self.session.get(url, params=dict(status='Open'))

        if not bool(response):
            error = response.json()
            code = error['error_code']
            if code == 'ETRACKERDISABLED':
                return []
            else:
                raise IOError('Failed to talk to %r %r' % (url, error))

        issues = []
        for result in response.json()[key2]:
            idx = six.text_type(result['id'])
            result['html_url'] = "/".join([self.base_url, repo, key3, idx])
            issues.append((repo, result))

        return issues

    def annotations(self, issue, issue_obj):
        url = issue['html_url']
        return self.build_annotations(
            ((
                c['user']['name'],
                c['comment'],
            ) for c in issue['comments']),
            issue_obj.get_processed_url(url)
        )

    def get_owner(self, issue):
        if issue[1]['assignee']:
            return issue[1]['assignee']['name']

    def filter_repos(self, repo):
        if self.exclude_repos:
            if repo in self.exclude_repos:
                return False

        if self.include_repos:
            if repo in self.include_repos:
                return True
            else:
                return False

        return True

    def issues(self):
        if self.tag:
            url = self.base_url + "/api/0/projects?tags=" + self.tag
            response = self.session.get(url)
            if not bool(response):
                raise IOError('Failed to talk to %r %r' % (url, response))

            all_repos = [r['name'] for r in response.json()['projects']]
        else:
            all_repos = [self.repo]

        repos = filter(self.filter_repos, all_repos)

        issues = []
        for repo in repos:
            issues.extend(self.get_issues(repo, ('issues', 'issues')))
            issues.extend(self.get_issues(repo, ('pull-requests', 'requests')))

        log.debug(" Found %i issues.", len(issues))
        issues = list(filter(self.include, issues))
        log.debug(" Pruned down to %i issues.", len(issues))

        for repo, issue in issues:
            # Stuff this value into the upstream dict for:
            # https://pagure.com/ralphbean/bugwarrior/issues/159
            issue['repo'] = repo

            issue_obj = self.get_issue_for_record(issue)
            extra = {
                'project': repo,
                'type': 'pull_request' if 'branch' in issue else 'issue',
                'annotations': self.annotations(issue, issue_obj)
            }
            issue_obj.update_extra(extra)
            yield issue_obj

    @classmethod
    def validate_config(cls, service_config, target):
        if 'tag' not in service_config and 'repo' not in service_config:
            die("[%s] has no 'pagure.tag' or 'pagure.repo'" % target)

        if 'base_url' not in service_config:
            die("[%s] has no 'pagure.base_url'" % target)

        super(PagureService, cls).validate_config(service_config, target)
