from twiggy import log

from bugwarrior.services import IssueService
from bugwarrior.config import die, get_service_password

import datetime
import requests


class BitbucketService(IssueService):
    base_api = 'https://api.bitbucket.org/1.0'
    base_url = 'http://bitbucket.org/'

    # A map of bitbucket priorities to taskwarrior priorities
    priorities = {
        'trivial': 'L',
        'minor': 'L',
        'major': 'M',
        'critical': 'H',
        'blocker': 'H',
    }

    def __init__(self, *args, **kw):
        super(BitbucketService, self).__init__(*args, **kw)

        self.auth = None
        if self.config.has_option(self.target, 'login'):
            login = self.config.get(self.target, 'login')
            password = self.config.get(self.target, 'passw')
            if not password or password.startswith('@oracle:'):
                username = self.config.get(self.target, 'username')
                service = "bitbucket://%s@bitbucket.org/%s" % (login, username)
                password = get_service_password(
                    service, login, oracle=password,
                    interactive=self.config.interactive)

            self.auth = (login, password)

    @classmethod
    def validate_config(cls, config, target):
        if not config.has_option(target, 'username'):
            die("[%s] has no 'username'" % target)

        # TODO -- validate other options

        IssueService.validate_config(config, target)

    # Note -- not actually rate limited, I think.
    def pull(self, tag):
        url = self.base_api + '/repositories/%s/issues/' % tag
        response = _getter(url, auth=self.auth)
        return [(tag, issue) for issue in response['issues']]

    def annotations(self, tag, issue):
        url = self.base_api + '/repositories/%s/issues/%i/comments' % (
            tag, issue['local_id'])
        response = _getter(url, auth=self.auth)
        _parse = lambda s: datetime.datetime.strptime(s[:10], "%Y-%m-%d")
        return dict([
            self.format_annotation(
                _parse(comment['utc_created_on']),
                comment['author_info']['username'],
                comment['content'],
            ) for comment in response
        ])

    def get_owner(self, issue):
        tag, issue = issue
        return issue.get('responsible', {}).get('username', None)

    def issues(self):
        user = self.config.get(self.target, 'username')

        url = self.base_api + '/users/' + user + '/'
        response = _getter(url, auth=self.auth)
        repos = [
            repo.get('slug') for repo in response.get('repositories')
            if repo.get('has_issues')
        ]

        issues = sum([self.pull(user + "/" + repo) for repo in repos], [])
        log.name(self.target).debug(" Found {0} total.", len(issues))

        # Build a url for each issue
        for i in range(len(issues)):
            issues[i][1]['url'] = self.base_url + "/".join(
                issues[i][1]['resource_uri'].split('/')[3:]
            ).replace('issues', 'issue')

        closed = ['resolved', 'duplicate', 'wontfix', 'invalid']
        not_resolved = lambda tup: tup[1]['status'] not in closed
        issues = filter(not_resolved, issues)
        issues = filter(self.include, issues)
        log.name(self.target).debug(" Pruned down to {0}", len(issues))

        return [dict(
            description=self.description(
                issue['title'], issue['url'],
                issue['local_id'], cls="issue"),
            project=tag.split('/')[1],
            priority=self.priorities.get(
                issue['priority'],
                self.default_priority,
            ),
            **self.annotations(tag, issue)
        ) for tag, issue in issues]


def _getter(url, auth):
    response = requests.get(url, auth=auth)

    # And.. if we didn't get good results, just bail.
    if response.status_code != 200:
        raise IOError(
            "Non-200 status code %r; %r; %r" % (
                response.status_code, url, response.json))

    if callable(response.json):
        # Newer python-requests
        return response.json()
    else:
        # Older python-requests
        return response.json
