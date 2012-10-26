from twiggy import log

import pygithub3

from bugwarrior.services import IssueService
from bugwarrior.config import die


def list_by_repo(self, user=None, repo=None):
    """ List issues for a repo; runtime patch against pygithub3. """

    params = dict()
    request = self.make_request(
        'issues.list_by_repo', user=user, repo=repo)
    return self._get_result(request, **params)


class GithubService(IssueService):
    def __init__(self, *args, **kw):
        super(GithubService, self).__init__(*args, **kw)

        login = self.config.get(self.target, 'login')
        passw = self.config.get(self.target, 'passw')
        auth = dict(login=login, password=passw)
        self.gh = pygithub3.Github(**auth)

        # Patch pygithub3 on the fly like an asshole.
        import types
        self.gh.issues.list_by_repo = types.MethodType(
            list_by_repo, self.gh.issues, type(self.gh.issues)
        )

    def _issues(self, tag):
        """ Grab all the issues """
        return [
            (tag, i) for i in
            self.gh.issues.list_by_repo(
                *tag.split('/')
            ).all()
        ]

    def _comments(self, tag, number):
        user, repo = tag.split('/')
        return self.gh.issues.comments.list(
            number=number, user=user, repo=repo
        ).all()

    def annotations(self, tag, issue):
        comments = self._comments(tag, issue.number)
        return dict([
            self.format_annotation(
                c.created_at,
                c.user.login,
                c.body,
            ) for c in comments])

    def _reqs(self, tag):
        """ Grab all the pull requests """
        return [
            (tag, i) for i in
            self.gh.pull_requests.list(*tag.split('/')).all()
        ]

    def get_owner(self, issue):
        # Currently unimplemented for github-proper
        # See validate_config(...) below.
        return None

    def issues(self):
        user = self.config.get(self.target, 'username')

        all_repos = self.gh.repos.list(user=user).all()

        # First get and prune all the real issues
        has_issues = lambda repo: repo.has_issues and repo.open_issues > 0
        repos = filter(has_issues, all_repos)
        issues = sum([self._issues(user + "/" + r.name) for r in repos], [])
        log.debug(" Found {0} total.", len(issues))
        issues = filter(self.include, issues)
        log.debug(" Pruned down to {0}", len(issues))

        # Next, get all the pull requests (and don't prune)
        has_requests = lambda repo: repo.forks > 1
        repos = filter(has_requests, all_repos)
        requests = sum([self._reqs(user + "/" + r.name) for r in repos], [])

        formatted_issues = [dict(
            description=self.description(
                issue.title, issue.html_url,
                issue.number, cls="issue"
            ),
            project=tag.split('/')[1],
            priority=self.default_priority,
            **self.annotations(tag, issue)
        ) for tag, issue in issues]

        formatted_requests = [{
            "description": self.description(
                request.title, request.html_url,
                request.number, cls="pull_request"
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
