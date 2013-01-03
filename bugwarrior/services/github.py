from twiggy import log

from bugwarrior.services import IssueService
from bugwarrior.config import die

import githubutils
import datetime
import time


class GithubService(IssueService):
    def __init__(self, *args, **kw):
        super(GithubService, self).__init__(*args, **kw)

        login = self.config.get(self.target, 'login')
        passw = self.config.get(self.target, 'passw')
        self.auth = (login, passw)

    def _issues(self, tag):
        """ Grab all the issues """
        return [
            (tag, i) for i in
            githubutils.get_issues(*tag.split('/'), auth=self.auth)
        ]

    def _comments(self, tag, number):
        user, repo = tag.split('/')
        return githubutils.get_comments(user, repo, number, auth=self.auth)

    def annotations(self, tag, issue):
        comments = self._comments(tag, issue['number'])
        return dict([
            self.format_annotation(
                datetime.datetime.fromtimestamp(time.mktime(time.strptime(
                    c['created_at'], "%Y-%m-%dT%H:%M:%SZ"))),
                c['user']['login'],
                c['body'],
            ) for c in comments])

    def _reqs(self, tag):
        """ Grab all the pull requests """
        return [
            (tag, i) for i in
            githubutils.get_pulls(*tag.split('/'), auth=self.auth)
        ]

    def get_owner(self, issue):
        # Currently unimplemented for github-proper
        # See validate_config(...) below.
        return None

    def issues(self):
        user = self.config.get(self.target, 'username')

        all_repos = githubutils.get_repos(username=user, auth=self.auth)

        # First get and prune all the real issues
        has_issues = lambda repo: repo['has_issues'] and \
                repo['open_issues_count'] > 0
        repos = filter(has_issues, all_repos)
        issues = sum([self._issues(user + "/" + r['name']) for r in repos], [])
        log.debug(" Found {0} total.", len(issues))
        issues = filter(self.include, issues)
        log.debug(" Pruned down to {0}", len(issues))

        # Next, get all the pull requests (and don't prune)
        has_requests = lambda repo: repo['forks'] > 1
        repos = filter(has_requests, all_repos)
        requests = sum([self._reqs(user + "/" + r['name']) for r in repos], [])

        formatted_issues = [dict(
            description=self.description(
                issue['title'], issue['html_url'],
                issue['number'], cls="issue"
            ),
            project=tag.split('/')[1],
            priority=self.default_priority,
            **self.annotations(tag, issue)
        ) for tag, issue in issues]

        formatted_requests = [{
            "description": self.description(
                request['title'], request['html_url'],
                request['number'], cls="pull_request"
            ),
            "project": tag.split('/')[1],
            "priority": self.default_priority,
        } for tag, request in requests]

        return formatted_issues + formatted_requests

    @classmethod
    def validate_config(cls, config, target):
        if not config.has_option(target, 'login'):
            die("[%s] has no 'login'" % target)

        if not config.has_option(target, 'passw'):
            die("[%s] has no 'passw'" % target)

        if not config.has_option(target, 'username'):
            die("[%s] has no 'username'" % target)

        if config.has_option(target, 'only_if_assigned'):
            die("[%s] - github does not currently support issue owners." %
                target)

        IssueService.validate_config(config, target)
