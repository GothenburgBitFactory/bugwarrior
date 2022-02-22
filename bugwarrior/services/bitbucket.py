import requests
import typing_extensions

from bugwarrior import config
from bugwarrior.services import IssueService, Issue, ServiceClient

import logging
log = logging.getLogger(__name__)


class BitbucketConfig(config.ServiceConfig, prefix='bitbucket'):
    service: typing_extensions.Literal['bitbucket']

    username: str
    login: str

    password: str = ''
    key: str = ''
    secret: str = ''

    include_repos: config.ConfigList = config.ConfigList([])
    exclude_repos: config.ConfigList = config.ConfigList([])
    filter_merge_requests: bool = False
    project_owner_prefix: bool = False


class BitbucketIssue(Issue):
    TITLE = 'bitbuckettitle'
    URL = 'bitbucketurl'
    FOREIGN_ID = 'bitbucketid'

    UDAS = {
        TITLE: {
            'type': 'string',
            'label': 'Bitbucket Title',
        },
        URL: {
            'type': 'string',
            'label': 'Bitbucket URL',
        },
        FOREIGN_ID: {
            'type': 'numeric',
            'label': 'Bitbucket Issue ID',
        }
    }
    UNIQUE_KEY = (URL, )

    PRIORITY_MAP = {
        'trivial': 'L',
        'minor': 'L',
        'major': 'M',
        'critical': 'H',
        'blocker': 'H',
    }

    def to_taskwarrior(self):
        return {
            'project': self.extra['project'],
            'priority': self.get_priority(),
            'annotations': self.extra['annotations'],

            self.URL: self.extra['url'],
            self.FOREIGN_ID: self.record['id'],
            self.TITLE: self.record['title'],
        }

    def get_default_description(self):
        return self.build_default_description(
            title=self.record['title'],
            url=self.get_processed_url(self.extra['url']),
            number=self.record['id'],
            cls='issue'
        )


class BitbucketService(IssueService, ServiceClient):
    ISSUE_CLASS = BitbucketIssue
    CONFIG_SCHEMA = BitbucketConfig

    BASE_API2 = 'https://api.bitbucket.org/2.0'
    BASE_URL = 'https://bitbucket.org/'

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)

        auth = {'oauth': (self.config.key, self.config.secret)}

        refresh_token = self.main_config.data.get('bitbucket_refresh_token')

        if not refresh_token:
            password = self.get_password('password', self.config.login)
            auth['basic'] = (self.config.login, password)

        if self.config.key and self.config.secret:
            if refresh_token:
                response = requests.post(
                    self.BASE_URL + 'site/oauth2/access_token',
                    data={'grant_type': 'refresh_token',
                          'refresh_token': refresh_token},
                    auth=auth['oauth']).json()
            else:
                response = requests.post(
                    self.BASE_URL + 'site/oauth2/access_token',
                    data={'grant_type': 'password',
                          'username': self.config.login,
                          'password': password},
                    auth=auth['oauth']).json()

                self.main_config.data.set('bitbucket_refresh_token',
                                          response['refresh_token'])

            auth['token'] = response['access_token']

        self.requests_kwargs = {}
        if 'token' in auth:
            self.requests_kwargs['headers'] = {
                'Authorization': 'Bearer ' + auth['token']}
        elif 'basic' in auth:
            self.requests_kwargs['auth'] = auth['basic']

    @staticmethod
    def get_keyring_service(config):
        return f"bitbucket://{config.login}@bitbucket.org/{config.username}"

    def filter_repos(self, repo_tag):
        repo = repo_tag.split('/').pop()

        if self.config.exclude_repos:
            if repo in self.config.exclude_repos:
                return False

        if self.config.include_repos:
            if repo in self.config.include_repos:
                return True
            else:
                return False

        return True

    def get_data(self, url):
        """ Perform a request to the fully qualified url and return json. """
        return self.json_response(requests.get(url, **self.requests_kwargs))

    def get_collection(self, url):
        """ Pages through an object collection from the bitbucket API.
        Returns an iterator that lazily goes through all the 'values'
        of all the pages in the collection. """
        url = self.BASE_API2 + url
        while url is not None:
            response = self.get_data(url)
            yield from response['values']
            url = response.get('next', None)

    def fetch_issues(self, tag):
        response = self.get_collection('/repositories/%s/issues/' % (tag))
        return [(tag, issue) for issue in response]

    def fetch_pull_requests(self, tag):
        response = self.get_collection('/repositories/%s/pullrequests/' % tag)
        return [(tag, issue) for issue in response]

    def get_annotations(self, tag, issue, issue_obj, url):
        response = self.get_collection(
            '/repositories/%s/pullrequests/%i/comments' % (tag, issue['id'])
        )
        return self.build_annotations(
            ((
                comment['user']['username'],
                comment['content']['raw'],
            ) for comment in response),
            issue_obj.get_processed_url(url)
        )

    def get_owner(self, issue):
        _, issue = issue
        assignee = issue.get('assignee', None)
        if assignee is not None:
            return assignee.get('username', None)

    def issues(self):
        user = self.config.username
        response = self.get_collection('/repositories/' + user + '/')
        repo_tags = list(filter(self.filter_repos, [
            repo['full_name'] for repo in response
            if repo.get('has_issues')
        ]))

        issues = sum((self.fetch_issues(repo) for repo in repo_tags), [])
        log.debug(" Found %i total.", len(issues))

        closed = ['resolved', 'duplicate', 'wontfix', 'invalid', 'closed']
        try:
            issues = [tup for tup in issues if tup[1]['status'] not in closed]
        except KeyError:  # Undocumented API change.
            issues = [tup for tup in issues if tup[1]['state'] not in closed]
        issues = list(filter(self.include, issues))
        log.debug(" Pruned down to %i", len(issues))

        for tag, issue in issues:
            issue_obj = self.get_issue_for_record(issue)
            tagParts = tag.split('/')
            projectName = tagParts[1]
            if self.config.project_owner_prefix:
                projectName = tagParts[0] + "." + projectName
            url = issue['links']['html']['href']
            extras = {
                'project': projectName,
                'url': url,
                'annotations': self.get_annotations(tag, issue, issue_obj, url)
            }
            issue_obj.update_extra(extras)
            yield issue_obj

        if not self.config.filter_merge_requests:
            pull_requests = sum(
                (self.fetch_pull_requests(repo) for repo in repo_tags), [])
            log.debug(" Found %i total.", len(pull_requests))

            closed = ['rejected', 'fulfilled']
            def not_resolved(tup): return tup[1]['state'] not in closed
            pull_requests = list(filter(not_resolved, pull_requests))
            pull_requests = list(filter(self.include, pull_requests))
            log.debug(" Pruned down to %i", len(pull_requests))

            for tag, issue in pull_requests:
                issue_obj = self.get_issue_for_record(issue)
                tagParts = tag.split('/')
                projectName = tagParts[1]
                if self.config.project_owner_prefix:
                    projectName = tagParts[0] + "." + projectName
                url = self.BASE_URL + '/'.join(
                    issue['links']['html']['href'].split('/')[3:]
                ).replace('pullrequests', 'pullrequest')
                extras = {
                    'project': projectName,
                    'url': url,
                    'annotations': self.get_annotations(
                        tag, issue, issue_obj, url)
                }
                issue_obj.update_extra(extras)
                yield issue_obj
