from __future__ import unicode_literals
from builtins import filter

import requests

from bugwarrior.services import IssueService, Issue, ServiceClient
from bugwarrior.config import asbool, aslist, die

import logging
log = logging.getLogger(__name__)

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
    CONFIG_PREFIX = 'bitbucket'

    BASE_API = 'https://api.bitbucket.org/1.0'
    BASE_API2 = 'https://api.bitbucket.org/2.0'
    BASE_URL = 'https://bitbucket.org/'

    def __init__(self, *args, **kw):
        super(BitbucketService, self).__init__(*args, **kw)

        key = self.config.get('key')
        secret = self.config.get('secret')
        auth = {'oauth': (key, secret)}

        refresh_token = self.config.data.get('bitbucket_refresh_token')

        if not refresh_token:
            login = self.config.get('login')
            password = self.get_password('password', login)
            auth['basic'] = (login, password)

        if key and secret:
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
                          'username': login,
                          'password': password},
                    auth=auth['oauth']).json()

                self.config.data.set('bitbucket_refresh_token',
                                     response['refresh_token'])

            auth['token'] = response['access_token']

        self.requests_kwargs = {}
        if 'token' in auth:
            self.requests_kwargs['headers'] = {
                'Authorization': 'Bearer ' + auth['token']}
        elif 'basic' in auth:
            self.requests_kwargs['auth'] = auth['basic']

        self.exclude_repos = self.config.get('exclude_repos', [], aslist)
        self.include_repos = self.config.get('include_repos', [], aslist)

        self.filter_merge_requests = self.config.get(
            'filter_merge_requests', default=False, to_type=asbool
        )

        self.project_owner_prefix = self.config.get(
            'project_owner_prefix', default=False, to_type=asbool
        )

    @staticmethod
    def get_keyring_service(service_config):
        login = service_config.get('login')
        username = service_config.get('username')
        return "bitbucket://%s@bitbucket.org/%s" % (login, username)

    def filter_repos(self, repo_tag):
        repo = repo_tag.split('/').pop()

        if self.exclude_repos:
            if repo in self.exclude_repos:
                return False

        if self.include_repos:
            if repo in self.include_repos:
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
            for value in response['values']:
                yield value
            url = response.get('next', None)

    @classmethod
    def validate_config(cls, service_config, target):
        if 'username' not in service_config:
            die("[%s] has no 'username'" % target)
        if 'login' not in service_config:
            die("[%s] has no 'login'" % target)

        IssueService.validate_config(service_config, target)

    def fetch_issues(self, tag):
        response = self.get_collection('/repositories/%s/issues/' % (tag))
        return [(tag, issue) for issue in response]

    def fetch_pull_requests(self, tag):
        response = self.get_collection('/repositories/%s/pullrequests/' % tag)
        return [(tag, issue) for issue in response]

    def get_annotations(self, tag, issue, issue_obj, url):
        response = self.get_data(
            self.BASE_API +
            '/repositories/%s/issues/%i/comments' % (tag, issue['id']))
        return self.build_annotations(
            ((
                comment['author_info']['username'],
                comment['content'],
            ) for comment in response),
            issue_obj.get_processed_url(url)
        )

    def get_annotations2(self, tag, issue, issue_obj, url):
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
        user = self.config.get('username')
        response = self.get_collection('/repositories/' + user + '/')
        repo_tags = list(filter(self.filter_repos, [
            repo['full_name'] for repo in response
            if repo.get('has_issues')
        ]))

        issues = sum([self.fetch_issues(repo) for repo in repo_tags], [])
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
            if self.project_owner_prefix:
                projectName = tagParts[0] + "." + projectName
            url = issue['links']['html']['href']
            extras = {
                'project': projectName,
                'url': url,
                'annotations': self.get_annotations(tag, issue, issue_obj, url)
            }
            issue_obj.update_extra(extras)
            yield issue_obj

        if not self.filter_merge_requests:
            pull_requests = sum(
                [self.fetch_pull_requests(repo) for repo in repo_tags], [])
            log.debug(" Found %i total.", len(pull_requests))

            closed = ['rejected', 'fulfilled']
            not_resolved = lambda tup: tup[1]['state'] not in closed
            pull_requests = list(filter(not_resolved, pull_requests))
            pull_requests = list(filter(self.include, pull_requests))
            log.debug(" Pruned down to %i", len(pull_requests))

            for tag, issue in pull_requests:
                issue_obj = self.get_issue_for_record(issue)
                tagParts = tag.split('/')
                projectName = tagParts[1]
                if self.project_owner_prefix:
                    projectName = tagParts[0] + "." + projectName
                url = self.BASE_URL + '/'.join(
                    issue['links']['html']['href'].split('/')[3:]
                ).replace('pullrequests', 'pullrequest')
                extras = {
                    'project': projectName,
                    'url': url,
                    'annotations': self.get_annotations2(tag, issue, issue_obj, url)
                }
                issue_obj.update_extra(extras)
                yield issue_obj
