import re
import six

from jinja2 import Template
from twiggy import log

from bugwarrior.config import asbool, die, get_service_password
from bugwarrior.services import IssueService, Issue

from . import githubutils


class GithubIssue(Issue):
    TITLE = 'githubtitle'
    BODY = 'githubbody'
    CREATED_AT = 'githubcreatedon'
    UPDATED_AT = 'githubupdatedat'
    MILESTONE = 'githubmilestone'
    URL = 'githuburl'
    TYPE = 'githubtype'
    NUMBER = 'githubnumber'

    UDAS = {
        TITLE: {
            'type': 'string',
            'label': 'Github Title',
        },
        BODY: {
            'type': 'string',
            'label': 'Github Body',
        },
        CREATED_AT: {
            'type': 'date',
            'label': 'Github Created',
        },
        UPDATED_AT: {
            'type': 'date',
            'label': 'Github Updated',
        },
        MILESTONE: {
            'type': 'numeric',
            'label': 'Github Milestone',
        },
        URL: {
            'type': 'string',
            'label': 'Github URL',
        },
        TYPE: {
            'type': 'string',
            'label': 'Github Type',
        },
        NUMBER: {
            'type': 'numeric',
            'label': 'Github Issue/PR #',
        },
    }
    UNIQUE_KEY = (URL, TYPE,)

    def to_taskwarrior(self):
        milestone = self.record['milestone']
        if milestone:
            milestone = milestone['id']

        body = self.record['body']
        if body:
            body = body.replace('\r\n', '\n')

        return {
            'project': self.extra['project'],
            'priority': self.origin['default_priority'],
            'annotations': self.extra.get('annotations', []),
            'tags': self.get_tags(),

            self.URL: self.record['html_url'],
            self.TYPE: self.extra['type'],
            self.TITLE: self.record['title'],
            self.BODY: body,
            self.MILESTONE: milestone,
            self.NUMBER: self.record['number'],
            self.CREATED_AT: self.parse_date(self.record['created_at']),
            self.UPDATED_AT: self.parse_date(self.record['updated_at'])
        }

    def get_tags(self):
        tags = []

        if not self.origin['import_labels_as_tags']:
            return tags

        context = self.record.copy()
        label_template = Template(self.origin['label_template'])

        for label_dict in self.record.get('labels', []):
            context.update({
                'label': label_dict['name']
            })
            tags.append(
                label_template.render(context)
            )

        return tags

    def get_default_description(self):
        return self.build_default_description(
            title=self.record['title'],
            url=self.get_processed_url(self.record['html_url']),
            number=self.record['number'],
            cls=self.extra['type'],
        )


class GithubService(IssueService):
    ISSUE_CLASS = GithubIssue
    CONFIG_PREFIX = 'github'

    def __init__(self, *args, **kw):
        super(GithubService, self).__init__(*args, **kw)

        login = self.config_get('login')
        password = self.config_get_default('password')
        if not password or password.startswith('@oracle:'):
            username = self.config_get('username')
            service = "github://%s@github.com/%s" % (login, username)
            password = get_service_password(
                service, login, oracle=password,
                interactive=self.config.interactive
            )
        self.auth = (login, password)

        self.exclude_repos = []
        if self.config_get_default('exclude_repos', None):
            self.exclude_repos = [
                item.strip() for item in
                self.config_get('exclude_repos').strip().split(',')
            ]

        self.include_repos = []
        if self.config_get_default('include_repos', None):
            self.include_repos = [
                item.strip() for item in
                self.config_get('include_repos').strip().split(',')
            ]

        self.import_labels_as_tags = self.config_get_default(
            'import_labels_as_tags', default=False, to_type=asbool
        )
        self.label_template = self.config_get_default(
            'label_template', default='{{label}}', to_type=six.text_type
        )

    def get_service_metadata(self):
        return {
            'import_labels_as_tags': self.import_labels_as_tags,
            'label_template': self.label_template,
        }

    def get_owned_repo_issues(self, tag):
        """ Grab all the issues """
        issues = {}
        for issue in githubutils.get_issues(*tag.split('/'), auth=self.auth):
            issues[issue['url']] = (tag, issue)
        return issues

    def get_directly_assigned_issues(self):
        project_matcher = re.compile(
            r'.*/repos/(?P<owner>[^/]+)/(?P<project>[^/]+)/.*'
        )
        issues = {}
        for issue in githubutils.get_directly_assigned_issues(auth=self.auth):
            match_dict = project_matcher.match(issue['url']).groupdict()
            issues[issue['url']] = (
                '{owner}/{project}'.format(
                    **match_dict
                ),
                issue
            )
        return issues

    def _comments(self, tag, number):
        user, repo = tag.split('/')
        return githubutils.get_comments(user, repo, number, auth=self.auth)

    def annotations(self, tag, issue):
        comments = self._comments(tag, issue['number'])
        return self.build_annotations(
            (
                c['user']['login'],
                c['body'],
            ) for c in comments
        )

    def _reqs(self, tag):
        """ Grab all the pull requests """
        return [
            (tag, i) for i in
            githubutils.get_pulls(*tag.split('/'), auth=self.auth)
        ]

    def get_owner(self, issue):
        if issue[1]['assignee']:
            return issue[1]['assignee']['login']

    def _filter_repos_base(self, repo):
        if self.exclude_repos:
            if repo['name'] in self.exclude_repos:
                return False

        if self.include_repos:
            if repo['name'] in self.include_repos:
                return True
            else:
                return False

        return True

    def filter_repos_for_prs(self, repo):
        if repo['forks'] < 1:
            return False
        else:
            return self._filter_repos_base(repo)

    def filter_repos_for_issues(self, repo):
        if not (repo['has_issues'] and repo['open_issues_count'] > 0):
            return False
        else:
            return self._filter_repos_base(repo)

    def issues(self):
        user = self.config.get(self.target, 'github.username')

        all_repos = githubutils.get_repos(username=user, auth=self.auth)
        assert(type(all_repos) == list)
        repos = filter(self.filter_repos_for_issues, all_repos)

        issues = {}
        for repo in repos:
            issues.update(
                self.get_owned_repo_issues(user + "/" + repo['name'])
            )
        issues.update(self.get_directly_assigned_issues())
        log.name(self.target).debug(" Found {0} total.", len(issues))
        issues = filter(self.include, issues.values())
        log.name(self.target).debug(" Pruned down to {0}", len(issues))

        # Next, get all the pull requests (and don't prune)
        repos = filter(self.filter_repos_for_prs, all_repos)
        requests = sum([self._reqs(user + "/" + r['name']) for r in repos], [])

        # For pull requests, github lists an 'issue' and a 'pull request' with
        # the same id and the same URL.  So, if we find any pull requests,
        # let's strip those out of the "issues" list so that we don't have
        # unnecessary duplicates.
        request_urls = [r[1]['html_url'] for r in requests]

        issues = [i for i in issues if not i[1]['html_url'] in request_urls]
        log.name(self.target).debug(" Added {0} pull requests", len(requests))

        for tag, issue in issues:
            extra = {
                'project': tag.split('/')[1],
                'type': 'issue',
                'annotations': self.annotations(tag, issue)
            }
            yield self.get_issue_for_record(issue, extra)

        for tag, request in requests:
            extra = {
                'project': tag.split('/')[1],
                'type': 'pull_request',
                'annotations': self.annotations(tag, request)
            }
            yield self.get_issue_for_record(request, extra)

    @classmethod
    def validate_config(cls, config, target):
        if not config.has_option(target, 'github.login'):
            die("[%s] has no 'github.login'" % target)

        if not config.has_option(target, 'github.password'):
            die("[%s] has no 'github.password'" % target)

        if not config.has_option(target, 'github.username'):
            die("[%s] has no 'github.username'" % target)

        super(GithubService, cls).validate_config(config, target)
