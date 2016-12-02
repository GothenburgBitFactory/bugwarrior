from builtins import filter
import re
import six

import requests
from jinja2 import Template

from bugwarrior.config import asbool, aslist, die
from bugwarrior.services import IssueService, Issue, ServiceClient

import logging
log = logging.getLogger(__name__)


class GithubClient(ServiceClient):
    def __init__(self, auth):
        self.auth = auth
        self.session = requests.Session()
        if 'token' in self.auth:
            token = self.auth['token']
            if isinstance(token, bytes):  # python3
                token = token.decode('utf-8')
            self.session.headers['Authorization'] = 'token ' + token

    def get_repos(self, username):
        user_repos = self._getter(
            "https://api.github.com/user/repos?per_page=100")
        public_repos = self._getter(
            "https://api.github.com/users/{username}/repos?per_page=100".format(
                username=username))
        return user_repos + public_repos

    def get_involved_issues(self, username):
        tmpl = "https://api.github.com/search/issues?q=involves%3A{username}%20state%3Aopen&per_page=100"
        url = tmpl.format(username=username)
        return self._getter(url, subkey='items')

    def get_issues(self, username, repo):
        tmpl = "https://api.github.com/repos/{username}/{repo}/issues?per_page=100"
        url = tmpl.format(username=username, repo=repo)
        return self._getter(url)

    def get_directly_assigned_issues(self):
        """ Returns all issues assigned to authenticated user.

        This will return all issues assigned to the authenticated user
        regardless of whether the user owns the repositories in which the
        issues exist.
        """
        url = "https://api.github.com/user/issues?per_page=100"
        return self._getter(url)

    def get_comments(self, username, repo, number):
        tmpl = "https://api.github.com/repos/{username}/{repo}/issues/" + \
            "{number}/comments?per_page=100"
        url = tmpl.format(username=username, repo=repo, number=number)
        return self._getter(url)

    def get_pulls(self, username, repo):
        tmpl = "https://api.github.com/repos/{username}/{repo}/pulls?per_page=100"
        url = tmpl.format(username=username, repo=repo)
        return self._getter(url)

    def _getter(self, url, subkey=None):
        """ Pagination utility.  Obnoxious. """

        kwargs = {}
        if 'basic' in self.auth:
            kwargs['auth'] = self.auth['basic']

        results = []
        link = dict(next=url)

        while 'next' in link:
            response = self.session.get(link['next'], **kwargs)
            json_res = self.json_response(response)

            if subkey is not None:
                json_res = json_res[subkey]

            results += json_res

            link = self._link_field_to_dict(response.headers.get('link', None))

        return results

    @staticmethod
    def _link_field_to_dict(field):
        """ Utility for ripping apart github's Link header field.
        It's kind of ugly.
        """

        if not field:
            return dict()

        return dict([
            (
                part.split('; ')[1][5:-1],
                part.split('; ')[0][1:-1],
            ) for part in field.split(', ')
        ])


class GithubIssue(Issue):
    TITLE = 'githubtitle'
    BODY = 'githubbody'
    CREATED_AT = 'githubcreatedon'
    UPDATED_AT = 'githubupdatedat'
    MILESTONE = 'githubmilestone'
    URL = 'githuburl'
    REPO = 'githubrepo'
    TYPE = 'githubtype'
    NUMBER = 'githubnumber'
    USER = 'githubuser'

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
            'type': 'string',
            'label': 'Github Milestone',
        },
        REPO: {
            'type': 'string',
            'label': 'Github Repo Slug',
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
        USER: {
            'type': 'string',
            'label': 'Github User',
        },
    }
    UNIQUE_KEY = (URL, TYPE,)

    def _normalize_label_to_tag(self, label):
        return re.sub(r'[^a-zA-Z0-9]', '_', label)

    def to_taskwarrior(self):
        milestone = self.record['milestone']
        if milestone:
            milestone = milestone['title']

        body = self.record['body']
        if body:
            body = body.replace('\r\n', '\n')

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
            self.USER: self.record['user']['login'],
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
                'label': self._normalize_label_to_tag(label_dict['name'])
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

        self.login = self.config_get('login')
        self.username = self.config_get('username')

        auth = {}
        token = self.config_get_default('token')
        if self.config_has('token'):
            token = self.config_get_password('token', self.login)
            auth['token'] = token
        else:
            password = self.config_get_password('password', self.login)
            auth['basic'] = (self.login, password)

        self.client = GithubClient(auth)

        self.exclude_repos = self.config_get_default('exclude_repos', [], aslist)
        self.include_repos = self.config_get_default('include_repos', [], aslist)

        self.import_labels_as_tags = self.config_get_default(
            'import_labels_as_tags', default=False, to_type=asbool
        )
        self.label_template = self.config_get_default(
            'label_template', default='{{label}}', to_type=six.text_type
        )
        self.filter_pull_requests = self.config_get_default(
            'filter_pull_requests', default=False, to_type=asbool
        )
        self.involved_issues = self.config_get_default(
            'involved_issues', default=False, to_type=asbool
        )

    @classmethod
    def get_keyring_service(cls, config, section):
        login = config.get(section, cls._get_key('login'))
        username = config.get(section, cls._get_key('username'))
        return "github://%s@github.com/%s" % (login, username)

    def get_service_metadata(self):
        return {
            'import_labels_as_tags': self.import_labels_as_tags,
            'label_template': self.label_template,
        }

    def get_owned_repo_issues(self, tag):
        """ Grab all the issues """
        issues = {}
        for issue in self.client.get_issues(*tag.split('/')):
            issues[issue['url']] = (tag, issue)
        return issues

    def get_involved_issues(self, user):
        """ Grab all 'interesting' issues """
        issues = {}
        for issue in self.client.get_involved_issues(user):
            url = issue['html_url']
            tag = re.match('.*github\\.com/(.*)/(issues|pull)/[^/]*$', url)
            if tag is None:
                log.critical(" Unrecognized issue URL: %s.", url)
                continue
            issues[url] = (tag.group(1), issue)
        return issues

    def get_directly_assigned_issues(self):
        project_matcher = re.compile(
            r'.*/repos/(?P<owner>[^/]+)/(?P<project>[^/]+)/.*'
        )
        issues = {}
        for issue in self.client.get_directly_assigned_issues():
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
        return self.client.get_comments(user, repo, number)

    def annotations(self, tag, issue, issue_obj):
        url = issue['html_url']
        annotations = []
        if self.annotation_comments:
            comments = self._comments(tag, issue['number'])
            log.debug(" got comments for %s", issue['html_url'])
            annotations = ((
                c['user']['login'],
                c['body'],
            ) for c in comments)
        return self.build_annotations(
            annotations,
            issue_obj.get_processed_url(url)
        )

    def _reqs(self, tag):
        """ Grab all the pull requests """
        return [
            (tag, i) for i in
            self.client.get_pulls(*tag.split('/'))
        ]

    def get_owner(self, issue):
        if issue[1]['assignee']:
            return issue[1]['assignee']['login']

    def filter_issues(self, issue):
        repo, _ = issue
        return self.filter_repo_name(repo.split('/')[-3])

    def filter_repos(self, repo):
        if repo['owner']['login'] != self.username:
            return False

        return self.filter_repo_name(repo['name'])

    def filter_repo_name(self, name):
        if self.exclude_repos:
            if name in self.exclude_repos:
                return False

        if self.include_repos:
            if name in self.include_repos:
                return True
            else:
                return False

        return True

    def include(self, issue):
        if 'pull_request' in issue[1] and not self.filter_pull_requests:
            return True
        return super(GithubService, self).include(issue)

    def issues(self):
        all_repos = self.client.get_repos(self.username)
        assert(type(all_repos) == list)
        repos = filter(self.filter_repos, all_repos)

        issues = {}
        if self.involved_issues:
            issues.update(
                filter(self.filter_issues,
                       self.get_involved_issues(self.username).items())
            )
        else:
            for repo in repos:
                issues.update(
                    self.get_owned_repo_issues(
                        self.username + "/" + repo['name'])
                )
        if self.config_get_default('include_user_issues', True, asbool):
            issues.update(
                filter(self.filter_issues,
                       self.get_directly_assigned_issues().items())
            )
        log.debug(" Found %i issues.", len(issues))
        issues = list(filter(self.include, issues.values()))
        log.debug(" Pruned down to %i issues.", len(issues))

        for tag, issue in issues:
            # Stuff this value into the upstream dict for:
            # https://github.com/ralphbean/bugwarrior/issues/159
            issue['repo'] = tag

            issue_obj = self.get_issue_for_record(issue)
            extra = {
                'project': tag.split('/')[1],
                'type': 'pull_request' if 'pull_request' in issue else 'issue',
                'annotations': self.annotations(tag, issue, issue_obj)
            }
            issue_obj.update_extra(extra)
            yield issue_obj

    @classmethod
    def validate_config(cls, config, target):
        if not config.has_option(target, 'github.login'):
            die("[%s] has no 'github.login'" % target)

        if not config.has_option(target, 'github.token') and \
           not config.has_option(target, 'github.password'):
            die("[%s] has no 'github.token' or 'github.password'" % target)

        if not config.has_option(target, 'github.username'):
            die("[%s] has no 'github.username'" % target)

        super(GithubService, cls).validate_config(config, target)
