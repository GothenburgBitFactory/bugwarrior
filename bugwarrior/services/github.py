from builtins import filter
import re
import six
from urllib.parse import urlparse

import requests
from six.moves.urllib.parse import quote_plus
from jinja2 import Template

from bugwarrior.config import asbool, aslist, die
from bugwarrior.services import IssueService, Issue, ServiceClient

import logging
log = logging.getLogger(__name__)


class GithubClient(ServiceClient):
    def __init__(self, host, auth):
        self.host = host
        self.auth = auth
        self.session = requests.Session()
        if 'token' in self.auth:
            authorization = 'token ' + self.auth['token']
            self.session.headers['Authorization'] = authorization

    def _api_url(self, path, **context):
        """ Build the full url to the API endpoint """
        if self.host == 'github.com':
            baseurl = "https://api.github.com"
        else:
            baseurl = "https://{}/api/v3".format(self.host)
        return baseurl + path.format(**context)

    def get_repos(self, username):
        user_repos = self._getter(self._api_url("/user/repos?per_page=100"))
        public_repos = self._getter(self._api_url(
            "/users/{username}/repos?per_page=100", username=username))
        return user_repos + public_repos

    def get_query(self, query):
        """Run a generic issue/PR query"""
        url = self._api_url(
            "/search/issues?q={query}&per_page=100", query=query)
        return self._getter(url, subkey='items')

    def get_issues(self, username, repo):
        url = self._api_url(
            "/repos/{username}/{repo}/issues?per_page=100",
            username=username, repo=repo)
        return self._getter(url)

    def get_directly_assigned_issues(self):
        """ Returns all issues assigned to authenticated user.

        This will return all issues assigned to the authenticated user
        regardless of whether the user owns the repositories in which the
        issues exist.
        """
        url = self._api_url("/user/issues?per_page=100")
        return self._getter(url)

    def get_comments(self, username, repo, number):
        url = self._api_url(
            "/repos/{username}/{repo}/issues/{number}/comments?per_page=100",
            username=username, repo=repo, number=number)
        return self._getter(url)

    def get_pulls(self, username, repo):
        url = self._api_url(
            "/repos/{username}/{repo}/pulls?per_page=100",
            username=username, repo=repo)
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

            # Warn about the mis-leading 404 error code.  See:
            # https://github.com/ralphbean/bugwarrior/issues/374
            if response.status_code == 404 and 'token' in self.auth:
                log.warn("A '404' from github may indicate an auth "
                         "failure. Make sure both that your token is correct "
                         "and that it has 'public_repo' and not 'public "
                         "access' rights.")

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
    CLOSED_AT = 'githubclosedon'
    MILESTONE = 'githubmilestone'
    URL = 'githuburl'
    REPO = 'githubrepo'
    TYPE = 'githubtype'
    NUMBER = 'githubnumber'
    USER = 'githubuser'
    NAMESPACE = 'githubnamespace'
    STATE = 'githubstate'

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
        CLOSED_AT: {
            'type': 'date',
            'label': 'GitHub Closed',
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
        NAMESPACE: {
            'type': 'string',
            'label': 'Github Namespace',
        },
        STATE: {
            'type': 'string',
            'label': 'GitHub State',
        }
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

        created = self.parse_date(self.record.get('created_at'))
        updated = self.parse_date(self.record.get('updated_at'))
        closed = self.parse_date(self.record.get('closed_at'))

        return {
            'project': self.extra['project'],
            'priority': self.origin['default_priority'],
            'annotations': self.extra.get('annotations', []),
            'tags': self.get_tags(),
            'entry': created,
            'end': closed,

            self.URL: self.record['html_url'],
            self.REPO: self.record['repo'],
            self.TYPE: self.extra['type'],
            self.USER: self.record['user']['login'],
            self.TITLE: self.record['title'],
            self.BODY: body,
            self.MILESTONE: milestone,
            self.NUMBER: self.record['number'],
            self.CREATED_AT: created,
            self.UPDATED_AT: updated,
            self.CLOSED_AT: closed,
            self.NAMESPACE: self.extra['namespace'],
            self.STATE: self.record.get('state', '')
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

        self.host = self.config.get('host', 'github.com')
        self.login = self.config.get('login')

        auth = {}
        token = self.config.get('token')
        if 'token' in self.config:
            token = self.get_password('token', self.login)
            auth['token'] = token
        else:
            password = self.get_password('password', self.login)
            auth['basic'] = (self.login, password)

        self.client = GithubClient(self.host, auth)

        self.exclude_repos = self.config.get('exclude_repos', [], aslist)
        self.include_repos = self.config.get('include_repos', [], aslist)

        self.username = self.config.get('username')
        self.filter_pull_requests = self.config.get(
            'filter_pull_requests', default=False, to_type=asbool
        )
        self.exclude_pull_requests = self.config.get(
            'exclude_pull_requests', default=False, to_type=asbool
        )
        self.involved_issues = self.config.get(
            'involved_issues', default=False, to_type=asbool
        )
        self.import_labels_as_tags = self.config.get(
            'import_labels_as_tags', default=False, to_type=asbool
        )
        self.label_template = self.config.get(
            'label_template', default='{{label}}', to_type=six.text_type
        )
        self.project_owner_prefix = self.config.get(
            'project_owner_prefix', default=False, to_type=asbool
        )

        self.query = self.config.get(
            'query',
            default='involves:{user} state:open'.format(
                user=self.username) if self.involved_issues else '',
            to_type=six.text_type
        )

    @staticmethod
    def get_keyring_service(service_config):
        login = service_config.get('login')
        username = service_config.get('username')
        host = service_config.get('host', default='github.com')
        return "github://{login}@{host}/{username}".format(
            login=login, username=username, host=host)

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

    def get_query(self, query):
        """ Grab all issues matching a github query """
        issues = {}
        for issue in self.client.get_query(query):
            url = issue['html_url']
            try:
                repo = self.get_repository_from_issue(issue)
            except ValueError as e:
                log.critical(e)
            else:
                issues[url] = (repo, issue)
        return issues

    def get_directly_assigned_issues(self):
        issues = {}
        for issue in self.client.get_directly_assigned_issues():
            repos = self.get_repository_from_issue(issue)
            issues[issue['url']] = (repos, issue)
        return issues

    @classmethod
    def get_repository_from_issue(cls, issue):
        if 'repo' in issue:
            return issue['repo']
        if 'repos_url' in issue:
            url = issue['repos_url']
        elif 'repository_url' in issue:
            url = issue['repository_url']
        else:
            raise ValueError("Issue has no repository url" + str(issue))
        tag = re.match('.*/([^/]*/[^/]*)$', url)
        if tag is None:
            raise ValueError("Unrecognized URL: {}.".format(url))
        return tag.group(1)

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
        if 'pull_request' in issue[1]:
            if self.exclude_pull_requests:
                return False
            if not self.filter_pull_requests:
                return True
        return super(GithubService, self).include(issue)

    def issues(self):
        issues = {}
        if self.query:
            issues.update(self.get_query(self.query))

        if self.config.get('include_user_repos', True, asbool):
            # Only query for all repos if an explicit
            # include_repos list is not specified.
            if self.include_repos:
                repos = self.include_repos
            else:
                all_repos = self.client.get_repos(self.username)
                repos = filter(self.filter_repos, all_repos)
                repos = [repo['name'] for repo in repos]

            for repo in repos:
                issues.update(
                    self.get_owned_repo_issues(
                        self.username + "/" + repo)
                )
        if self.config.get('include_user_issues', True, asbool):
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
            tagParts = tag.split('/')
            projectName = tagParts[1]
            if self.project_owner_prefix:
                projectName = tagParts[0]+"."+projectName
            extra = {
                'project': projectName,
                'type': 'pull_request' if 'pull_request' in issue else 'issue',
                'annotations': self.annotations(tag, issue, issue_obj),
                'namespace': self.username,
            }
            issue_obj.update_extra(extra)
            yield issue_obj

    @classmethod
    def validate_config(cls, service_config, target):
        if 'login' not in service_config:
            die("[%s] has no 'github.login'" % target)

        if 'token' not in service_config and 'password' not in service_config:
            die("[%s] has no 'github.token' or 'github.password'" % target)

        if 'username' not in service_config:
            die("[%s] has no 'github.username'" % target)

        super(GithubService, cls).validate_config(service_config, target)
