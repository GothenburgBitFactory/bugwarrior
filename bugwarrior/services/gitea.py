#/home/joybuke/Documents/ComputerScience/Projects/Personal/bugwarrior/bugwarrior/services coding: utf-8
# gitea.py
"""Bugwarrior service support class for Gitea

Available classes:
- GiteaClient(ServiceClient): Constructs Gitea API strings
- GiteaIssue(Issue): TaskWarrior Interface
- GiteaService(IssueService): Engine for firing off requests

Todo:
    * Add token support
    * Flesh out more features offered by gitea api
"""
from builtins import filter
import logging
import pathlib
import re
import sys
from urllib.parse import urlparse
from urllib.parse import quote_plus

import requests
from six.moves.urllib.parse import quote_plus
import typing_extensions
from jinja2 import Template

from bugwarrior import config
from bugwarrior.services import IssueService, Issue, ServiceClient

log = logging.getLogger(__name__)  # pylint: disable-msg=C0103

class GiteaConfig(config.ServiceConfig):
    service: typing_extensions.Literal['gitea']

    host = "gitea.com"
    login: str
    token: str
    username: str
    password: str
    exclude_repos = config.ConfigList([])
    include_repos = config.ConfigList([])

    def get(self, key, default=None, to_type=None):
        try:
            value = self.config_parser.get(self.service_target, self._get_key(key))
            if to_type:
                return to_type(value)
            return value
        except:
            return default


class GiteaClient(ServiceClient):
    """Builds Gitea API strings
    Args:
        host (str): remote gitea server
        auth (dict): authentication credentials

    Attributes:
        host (str): remote gitea server
        auth (dict): authentication credentials
        session (requests.Session): requests persist settings

    Publics Functions:
    - get_repos:
    - get_query:
    - get_issues:
    - get_directly_assigned_issues:
    - get_comments:
    - get_pulls:
    """
    def __init__(self, host, auth):
        self.host = host
        self.auth = auth
        self.session = requests.Session()
        if 'token' in self.auth:
            authorization = 'token ' + self.auth['token']
            self.session.headers['Authorization'] = authorization

    def _api_url(self, path, **context):
        """ Build the full url to the API endpoint """
        # TODO add token support
        if 'basic' in self.auth:
            (username, password) = self.auth['basic']
            baseurl = 'https://{user}:{secret}@{host}/api/v1'.format(
                host=self.host,
                user=username,
                secret=quote_plus(password))
        if 'token' in self.auth:
            baseurl = 'https://{host}/api/v1'.format(
                host=self.host)
        return baseurl + path.format(**context)

    # TODO Modify these for gitea support
    def get_repos(self, username):
        # user_repos = self._getter(self._api_url("/user/repos?per_page=100"))
        public_repos = self._getter(self._api_url(
            '/users/{username}/repos', username=username))
        return public_repos

    def get_query(self, query):
        """Run a generic issue/PR query"""
        url = self._api_url(
            '/search/issues?q={query}&per_page=100', query=query)
        return self._getter(url, subkey='items')

    def get_issues(self, username, repo):
        url = self._api_url(
            '/repos/{username}/{repo}/issues?per_page=100',
            username=username, repo=repo)
        return self._getter(url)

    def get_directly_assigned_issues(self, username):
        """ Returns all issues assigned to authenticated user.

        This will return all issues assigned to the authenticated user
        regardless of whether the user owns the repositories in which the
        issues exist.
        """
        url = self._api_url('/repos/issues/search',
                            username=username, assignee=True)
        return self._getter(url, passedParams={'assigned': True, 'limit': 100}) #TODO: make the limit configurable

    # TODO close to gitea format: /comments/{id}
    def get_comments(self, username, repo, number):
        url = self._api_url(
            '/repos/{username}/{repo}/issues/{number}/comments?per_page=100',
            username=username, repo=repo, number=number)
        return self._getter(url)

    def get_pulls(self, username, repo):
        url = self._api_url(
            '/repos/{username}/{repo}/pulls?per_page=100',
            username=username, repo=repo)
        return self._getter(url)

    def _getter(self, url, subkey=None, passedParams={}):
        """ Pagination utility.  Obnoxious. """

        kwargs = {}
        if 'basic' in self.auth:
            kwargs['auth'] = self.auth['basic']

        results = []
        link = dict(next=url)

        while 'next' in link:
            response = self.session.get(link['next'], params=passedParams, **kwargs)

            # Warn about the mis-leading 404 error code.  See:
            # https://gitea.com/ralphbean/bugwarrior/issues/374
            # TODO this is a copy paste from github.py, see what gitea produces
            if response.status_code == 404 and 'token' in self.auth:
                log.warning('A \'404\' from gitea may indicate an auth '
                            'failure. Make sure both that your token is correct '
                            'and that it has \'public_repo\' and not \'public '
                            'access\' rights.')

            json_res = self.json_response(response)

            if subkey is not None:
                json_res = json_res[subkey]

            results += json_res

            link = self._link_field_to_dict(response.headers.get('link', None))

        return results

    # TODO: just copied from github.py
    @staticmethod
    def _link_field_to_dict(field):
        """ Utility for ripping apart gitea's Link header field.
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


class GiteaIssue(Issue):
    TITLE = 'giteatitle'
    BODY = 'giteabody'
    CREATED_AT = 'giteacreatedon'
    UPDATED_AT = 'giteaupdatedat'
    CLOSED_AT = 'giteaclosedon'
    MILESTONE = 'giteamilestone'
    URL = 'giteaurl'
    REPO = 'gitearepo'
    TYPE = 'giteatype'
    NUMBER = 'giteanumber'
    USER = 'giteauser'
    NAMESPACE = 'giteanamespace'
    STATE = 'giteastate'

    UDAS = {
        TITLE: {
            'type': 'string',
            'label': 'Gitea Title',
        },
        BODY: {
            'type': 'string',
            'label': 'Gitea Body',
        },
        CREATED_AT: {
            'type': 'date',
            'label': 'Gitea Created',
        },
        UPDATED_AT: {
            'type': 'date',
            'label': 'Gitea Updated',
        },
        CLOSED_AT: {
            'type': 'date',
            'label': 'Gitea Closed',
        },
        MILESTONE: {
            'type': 'string',
            'label': 'Gitea Milestone',
        },
        REPO: {
            'type': 'string',
            'label': 'Gitea Repo Slug',
        },
        URL: {
            'type': 'string',
            'label': 'Gitea URL',
        },
        TYPE: {
            'type': 'string',
            'label': 'Gitea Type',
        },
        NUMBER: {
            'type': 'numeric',
            'label': 'Gitea Issue/PR #',
        },
        USER: {
            'type': 'string',
            'label': 'Gitea User',
        },
        NAMESPACE: {
            'type': 'string',
            'label': 'Gitea Namespace',
        },
        STATE: {
            'type': 'string',
            'label': 'Gitea State',
        }
    }
    UNIQUE_KEY = (URL, TYPE,)

    @staticmethod
    def _normalize_label_to_tag(label):
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
            'priority': self.config.default_priority,
            'annotations': self.extra.get('annotations', []),
            'tags': self.get_tags(),
            'entry': created,
            'end': closed,

            self.URL: self.record['url'],
            self.REPO: self.record['repository'],
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

        if not self.config.get('import_labels_as_tags'):
            return tags

        context = self.record.copy()
        label_template = Template(self.config.get('label_template'))

        for label_dict in self.record.get('labels', []):
            context.update({
                'label': self._normalize_label_to_tag(label_dict['name'])
            })
            tags.append(
                label_template.render(context)
            )

        return tags

    def get_default_description(self):
        log.info('In get_default_description')
        return self.build_default_description(
            title=self.record['title'],
            url=self.get_processed_url(self.record['url']),
            number=self.record['number'],
            cls=self.extra['type'],
        )


class GiteaService(IssueService):
    ISSUE_CLASS = GiteaIssue
    CONFIG_SCHEMA = GiteaConfig
    CONFIG_PREFIX = 'gitea'

    def __init__(self, *args, **kw):
        super(GiteaService, self).__init__(*args, **kw)

        auth = {}
        token = self.config.token
        self.login = self.config.login
        if hasattr(self.config, 'token'):
            token = self.get_password('token', login=self.login)
            auth['token'] = token
        elif hasattr(self.config.hasattr, 'password'):
            password = self.get_password('password', login=self.login)
            auth['basic'] = (self.login, password)
        else:
            #Probably should be called by validate_config, but I don't care to fix that.
            logging.critical("ERROR! Neither token or password was provided in config!")
            sys.exit(1)

        self.client = GiteaClient(host=self.config.host, auth=auth)

        self.host = self.config.host

        self.exclude_repos = self.config.exclude_repos
        self.include_repos = self.config.include_repos

        self.username = self.config.username
        self.filter_pull_requests = self.config.get(
            'filter_pull_requests', default=False, to_type=bool
        )
        self.exclude_pull_requests = self.config.get(
            'exclude_pull_requests', default=False, to_type=bool
        )
        self.involved_issues = self.config.get(
            'involved_issues', default=False, to_type=bool
        )
        self.import_labels_as_tags = self.config.get(
            'import_labels_as_tags', default=False, to_type=bool
        )
        self.label_template = self.config.get(
            'label_template', default='{{label}}', to_type=bool
        )
        self.project_owner_prefix = self.config.get(
            'project_owner_prefix', default=False, to_type=bool
        )

        self.query = self.config.get(
            'query',
            default='involves:{user} state:open'.format(
                user=self.username) if self.involved_issues else '',
            to_type=str
        )

    @staticmethod
    def get_keyring_service(service_config):
        #TODO grok this
        login = service_config.login
        username = service_config.username
        host = service_config.host
        return 'gitea://{login}@{host}/{username}'.format(
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
        """ Grab all issues matching a gitea query """
        log.info('In get_query')
        issues = {}
        for issue in self.client.get_query(query):
            url = issue['url']
            try:
                repo = self.get_repository_from_issue(issue)
            except ValueError as e:
                log.critical(e)
            else:
                issues[url] = (repo, issue)
        return issues

    def get_directly_assigned_issues(self, username):
        issues = {}
        for issue in self.client.get_directly_assigned_issues(self.username):
            repos = self.get_repository_from_issue(issue)
            issues[issue['url']] = (repos, issue)
        return issues

    @classmethod
    def get_repository_from_issue(cls, issue):
        if 'repository' in issue:
            url = issueloc=issue["html_url"]
        else:
            raise ValueError('Issue has no repository url' + str(issue))

        #Literal cargo-cult crap, idk if this should be kept
        tag = re.match('.*/([^/]*/[^/]*)$', url)
        if tag is None:
            raise ValueError('Unrecognized URL: {}.'.format(url))
        
        return url.rsplit("/",2)[0]

    def _comments(self, tag, number):
        user, repo = tag.split('/')
        return self.client.get_comments(user, repo, number)

    def annotations(self, tag, issue, issue_obj):
        log.info('in Annotations')
        #log.info(repr(issue))
        log.info('body: {}'.format(issue['body']))
        url = issue['url']
        annotations = []
        if self.annotation_comments:
            comments = self._comments(tag, issue['body'])
            # log.info(" got comments for %s", issue['url'])
            annotations = ((
                c['user']['login'],
                c['body'],
            ) for c in comments)
        annotations_result = self.build_annotations(
            annotations,
            issue_obj.get_processed_url(url))
        log.info('annotations: {}'.format(annotations_result))
        return annotations_result

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
        return super(GiteaService, self).include(issue)

    def issues(self):
        issues = {}
        if self.query:
            issues.update(self.get_query(self.query))

        if self.config.get('include_user_repos', True, bool):
            # Only query for all repos if an explicit
            # include_repos list is not specified.
            if self.include_repos:
                repos = self.include_repos
            else:
                all_repos = self.client.get_repos(self.username)
                repos = filter(self.filter_repos, all_repos)
                repos = [repo['name'] for repo in repos]

            for repo in repos:
                log.info('Found repo: {}'.format(repo))
                issues.update(
                    self.get_owned_repo_issues(
                        self.username + '/' + repo)
                )
            issues.update(
                filter(self.filter_issues,
                       self.get_directly_assigned_issues(self.username).items())
            )

        log.info(' Found %i issues.', len(issues))  # these were debug logs
        issues = list(filter(self.include, issues.values()))
        log.info(' Pruned down to %i issues.', len(issues))  # these were debug logs

        for tag, issue in issues:
            # Stuff this value into the upstream dict for:
            # https://gitea.com/ralphbean/bugwarrior/issues/159
            projectName = issue['repository']["name"]

            issue_obj = self.get_issue_for_record(issue)
            if self.project_owner_prefix:
                projectName = issue['repository']["owner"] +'.'+projectName
            extra = {
                'project': projectName,
                'type': 'pull_request' if 'pull_request' in issue else 'issue',
                'annotations': [issue['body']],
                'namespace': self.username,
            }
            issue_obj.update_extra(extra)
            yield issue_obj

