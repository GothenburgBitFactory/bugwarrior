from twiggy import log

import github2.client

from bugwarrior.services import IssueService
from bugwarrior.config import die
from bugwarrior.util import rate_limit


class GithubService(IssueService):
    def __init__(self, *args, **kw):
        super(GithubService, self).__init__(*args, **kw)
        self.ghc = github2.client.Github()

    @rate_limit(limit_amount=50, limit_period=60)
    def _issues(self, tag):
        """ Grab all the issues """
        return [(tag, i) for i in self.ghc.issues.list(tag)]

    @rate_limit(limit_amount=50, limit_period=60)
    def _comments(self, tag, number):
        return self.ghc.issues.comments(tag, number)

    def annotations(self, tag, issue):
        comments = self._comments(tag, issue.number)
        return dict([
            self.format_annotation(
                c.created_at,
                c.user,
                c.body,
            ) for c in comments])

    @rate_limit(limit_amount=50, limit_period=60)
    def _reqs(self, tag):
        """ Grab all the pull requests """
        return [(tag, i) for i in self.ghc.pull_requests.list(tag)]

    def get_owner(self, issue):
        # Currently unimplemented for github-proper
        # See validate_config(...) below.
        return None

    def issues(self):
        user = self.config.get(self.target, 'username')

        all_repos, page = [], 1
        log.debug(" Getting ready to get list of all repos.", page)
        while True:
            log.debug(" Getting {0}th page of repos.", page)
            new_repos = self.ghc.repos.list(user, page)
            if not new_repos:
                break
            all_repos += new_repos
            page += 1

        # First get and prune all the real issues
        has_issues = lambda repo: repo.has_issues  # and repo.open_issues > 0
        repos = filter(has_issues, all_repos)
        issues = sum([self._issues(user + "/" + r.name) for r in repos], [])
        log.debug(" Found {0} total.", len(issues))
        issues = filter(self.include, issues)
        log.debug(" Pruned down to {0}", len(issues))

        # Next, get all the pull requests (and don't prune)
        has_requests = lambda repo: repo.forks > 1
        repos = filter(has_requests, all_repos)
        requests = sum([self._reqs(user + "/" + r.name) for r in repos], [])

        return [dict(
            description=self.description(
                issue.title, issue.html_url,
                issue.number, cls="issue"
            ),
            project=tag.split('/')[1],
            priority=self.default_priority,
            **self.annotations(tag, issue)
        ) for tag, issue in issues] + [{
            "description": self.description(
                request.title, request.html_url,
                request.number, cls="pull_request"
            ),
            "project": tag.split('/')[1],
            "priority": self.default_priority,
        } for tag, request in requests]

    @classmethod
    def validate_config(cls, config, target):
        if not config.has_option(target, 'username'):
            die("[%s] has no 'username'" % target)

        if config.has_option(target, 'only_if_assigned'):
            die("[%s] - github does not currently support issue owners." %
                target)

        IssueService.validate_config(config, target)
