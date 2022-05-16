import datetime
import pytz

import pydantic
import requests
import typing_extensions

from bugwarrior import config
from bugwarrior.services import IssueService, Issue

import logging
log = logging.getLogger(__name__)


class PagureConfig(config.ServiceConfig, prefix='pagure'):
    # strictly required
    service: typing_extensions.Literal['pagure']
    base_url: config.StrippedTrailingSlashUrl

    # conditionally required
    tag: str = ''
    repo: str = ''

    # optional
    include_repos: config.ConfigList = config.ConfigList([])
    exclude_repos: config.ConfigList = config.ConfigList([])
    import_tags: bool = False
    tag_template: str = '{{label}}'

    @pydantic.root_validator
    def require_tag_or_repo(cls, values):
        if not values['tag'] and not values['repo']:
            raise ValueError(
                'section requires one of:\npagure.tag\npagure.repo')
        return values


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
        return self.get_tags_from_labels(self.record.get('tags', []),
                                         toggle_option='import_tags',
                                         template_option='tag_template')

    def get_default_description(self):
        return self.build_default_description(
            title=self.record['title'],
            url=self.get_processed_url(self.record['html_url']),
            number=self.record['id'],
            cls=self.extra['type'],
        )


class PagureService(IssueService):
    ISSUE_CLASS = PagureIssue
    CONFIG_SCHEMA = PagureConfig

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)

        self.session = requests.Session()

    def get_service_metadata(self):
        return {
            'import_tags': self.config.import_tags,
            'tag_template': self.config.tag_template,
        }

    def get_issues(self, repo, keys):
        """ Grab all the issues """
        key1, key2 = keys
        key3 = key1[:-1]  # Just the singular form of key1

        url = self.config.base_url + "/api/0/" + repo + "/" + key1
        response = self.session.get(url, params=dict(status='Open'))

        if not bool(response):
            error = response.json()
            code = error['error_code']
            if code == 'ETRACKERDISABLED':
                return []
            else:
                raise OSError('Failed to talk to %r %r' % (url, error))

        issues = []
        for result in response.json()[key2]:
            idx = str(result['id'])
            result['html_url'] = "/".join([
                self.config.base_url, repo, key3, idx])
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
        if repo in self.config.exclude_repos:
            return False

        if self.config.include_repos:
            if repo in self.config.include_repos:
                return True
            else:
                return False

        return True

    def issues(self):
        if self.config.tag:
            url = (self.config.base_url +
                   "/api/0/projects?tags=" + self.config.tag)
            response = self.session.get(url)
            if not bool(response):
                raise OSError('Failed to talk to %r %r' % (url, response))

            all_repos = [r['name'] for r in response.json()['projects']]
        else:
            all_repos = [self.config.repo]

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
