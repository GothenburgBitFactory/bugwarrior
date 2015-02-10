import requests
from twiggy import log

from bugwarrior.services import IssueService, Issue
from bugwarrior.config import asbool, die, get_service_password


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
            'type': 'string',
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
            self.FOREIGN_ID: self.record['local_id'],
            self.TITLE: self.record['title'],
        }

    def get_default_description(self):
        return self.build_default_description(
            title=self.record['title'],
            url=self.get_processed_url(self.extra['url']),
            number=self.record['local_id'],
            cls='issue'
        )


class BitbucketService(IssueService):
    ISSUE_CLASS = BitbucketIssue
    CONFIG_PREFIX = 'bitbucket'

    BASE_API = 'https://api.bitbucket.org/1.0'
    BASE_API2 = 'https://api.bitbucket.org/2.0'
    BASE_URL = 'https://bitbucket.org/'

    def __init__(self, *args, **kw):
        super(BitbucketService, self).__init__(*args, **kw)

        self.auth = None
        if self.config_get_default('login'):
            login = self.config_get('login')
            password = self.config_get_default('password')
            if not password or password.startswith('@oracle:'):
                username = self.config_get('username')
                password = get_service_password(
                    self.get_keyring_service(self.config, self.target),
                    login, oracle=password,
                    interactive=self.config.interactive)

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

        self.filter_merge_requests = self.config_get_default(
            'filter_merge_requests', default=False, to_type=asbool
        )

    @classmethod
    def get_keyring_service(cls, config, section):
        login = config.get(section, cls._get_key('login'))
        username = config.get(section, cls._get_key('username'))
        return "bitbucket://%s@bitbucket.org/%s" % (login, username)

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

    def get_data2(self, url):
        response = requests.get(self.BASE_API2 + url, auth=self.auth)

        # And.. if we didn't get good results, just bail.
        if response.status_code != 200:
            raise IOError(
                "Non-200 status code %r; %r; %r" % (
                    response.status_code, url, response.text,
                )
            )
        if callable(response.json):
            # Newer python-requests
            return response.json()
        else:
            # Older python-requests
            return response.json

    def get_data(self, url):
        response = requests.get(self.BASE_API + url, auth=self.auth)

        # And.. if we didn't get good results, just bail.
        if response.status_code != 200:
            raise IOError(
                "Non-200 status code %r; %r; %r" % (
                    response.status_code, url, response.text,
                )
            )
        if callable(response.json):
            # Newer python-requests
            return response.json()
        else:
            # Older python-requests
            return response.json

    @classmethod
    def validate_config(cls, config, target):
        if not config.has_option(target, 'bitbucket.username'):
            die("[%s] has no 'username'" % target)

        IssueService.validate_config(config, target)

    def fetch_issues(self, tag):
        response = self.get_data('/repositories/%s/issues/' % (tag))
        return [(tag, issue) for issue in response['issues']]

    def fetch_pull_requests(self, tag):
        response = self.get_data2('/repositories/%s/pullrequests/' % tag)
        return [(tag, issue) for issue in response['values']]

    def get_annotations(self, tag, issue, issue_obj, url):
        response = self.get_data(
            '/repositories/%s/issues/%i/comments' % (tag, issue['local_id'])
        )
        return self.build_annotations(
            ((
                comment['author_info']['username'],
                comment['content'],
            ) for comment in response),
            issue_obj.get_processed_url(url)
        )

    def get_annotations2(self, tag, issue, issue_obj, url):
        response = self.get_data2(
            '/repositories/%s/pullrequests/%i/comments' % (tag, issue['id'])
        )
        return self.build_annotations(
            ((
                comment['user']['username'],
                comment['content']['raw'],
            ) for comment in response['values']),
            issue_obj.get_processed_url(url)
        )

    def get_owner(self, issue):
        tag, issue = issue
        return issue.get('responsible', {}).get('username', None)

    def issues(self):
        user = self.config.get(self.target, 'bitbucket.username')
        response = self.get_data('/users/' + user + '/')
        all_repos = [
            repo.get('slug') for repo in response.get('repositories')
            if repo.get('has_issues')
        ]
        repos = filter(self.filter_repos, all_repos)

        issues = sum([self.fetch_issues(user + "/" + repo) for repo in repos], [])
        log.name(self.target).debug(" Found {0} total.", len(issues))

        closed = ['resolved', 'duplicate', 'wontfix', 'invalid']
        not_resolved = lambda tup: tup[1]['status'] not in closed
        issues = filter(not_resolved, issues)
        issues = filter(self.include, issues)
        log.name(self.target).debug(" Pruned down to {0}", len(issues))

        for tag, issue in issues:
            issue_obj = self.get_issue_for_record(issue)
            url = self.BASE_URL + '/'.join(
                issue['resource_uri'].split('/')[3:]
            ).replace('issues', 'issue')
            extras = {
                'project': tag.split('/')[1],
                'url': url,
                'annotations': self.get_annotations(tag, issue, issue_obj, url)
            }
            issue_obj.update_extra(extras)
            yield issue_obj

        if not self.filter_merge_requests:
            pull_requests = sum([self.fetch_pull_requests(user + "/" + repo) for repo in repos], [])
            log.name(self.target).debug(" Found {0} total.", len(pull_requests))

            closed = ['rejected', 'fulfilled']
            not_resolved = lambda tup: tup[1]['state'] not in closed
            pull_requests = filter(not_resolved, pull_requests)
            pull_requests = filter(self.include, pull_requests)
            log.name(self.target).debug(" Pruned down to {0}", len(pull_requests))

            for tag, issue in pull_requests:
                # Pull requests are only accessible over API v2.0 which has
                # this difference.
                issue['local_id'] = issue['id']

                issue_obj = self.get_issue_for_record(issue)
                url = self.BASE_URL + '/'.join(
                    issue['links']['html']['href'].split('/')[3:]
                ).replace('pullrequests', 'pullrequest')
                extras = {
                    'project': tag.split('/')[1],
                    'url': url,
                    'annotations': self.get_annotations2(tag, issue, issue_obj, url)
                }
                issue_obj.update_extra(extras)
                yield issue_obj
