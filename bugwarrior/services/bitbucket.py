import requests
from twiggy import log

from bugwarrior.services import IssueService, Issue
from bugwarrior.config import die, get_service_password


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
    BASE_URL = 'http://bitbucket.org/'

    def __init__(self, *args, **kw):
        super(BitbucketService, self).__init__(*args, **kw)

        self.auth = None
        if self.config_get_default('login'):
            login = self.config_get('login')
            password = self.config_get_default('password')
            if not password or password.startswith('@oracle:'):
                username = self.config_get('username')
                service = "bitbucket://%s@bitbucket.org/%s" % (login, username)
                password = get_service_password(
                    service, login, oracle=password,
                    interactive=self.config.interactive)

            self.auth = (login, password)

    def get_data(self, url):
        response = requests.get(self.BASE_API + url, auth=self.auth)

        # And.. if we didn't get good results, just bail.
        if response.status_code != 200:
            raise IOError(
                "Non-200 status code %r; %r; %r" % (
                    response.status_code, url, response.json
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

    def pull(self, tag):
        response = self.get_data('/repositories/%s/issues/' % tag)
        return [(tag, issue) for issue in response['issues']]

    def get_annotations(self, tag, issue):
        response = self.get_data(
            '/repositories/%s/issues/%i/comments' % (tag, issue['local_id'])
        )
        return self.build_annotations(
            (
                comment['author_info']['username'],
                comment['content'],
            ) for comment in response
        )

    def get_owner(self, issue):
        tag, issue = issue
        return issue.get('responsible', {}).get('username', None)

    def issues(self):
        user = self.config.get(self.target, 'bitbucket.username')
        response = self.get_data('/users/' + user + '/')
        repos = [
            repo.get('slug') for repo in response.get('repositories')
            if repo.get('has_issues')
        ]

        issues = sum([self.pull(user + "/" + repo) for repo in repos], [])
        log.name(self.target).debug(" Found {0} total.", len(issues))

        closed = ['resolved', 'duplicate', 'wontfix', 'invalid']
        not_resolved = lambda tup: tup[1]['status'] not in closed
        issues = filter(not_resolved, issues)
        issues = filter(self.include, issues)
        log.name(self.target).debug(" Pruned down to {0}", len(issues))

        for tag, issue in issues:
            extras = {
                'project': tag.split('/')[1],
                'url': self.BASE_URL + '/'.join(
                    issue['resource_uri'].split('/')[3:]
                ).replace('issues', 'issue'),
                'annotations': self.get_annotations(tag, issue)
            }
            yield self.get_issue_for_record(issue, extras)
