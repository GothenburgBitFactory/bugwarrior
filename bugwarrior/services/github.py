import github2.client

from bugwarrior.services import IssueService
from bugwarrior.config import die
from bugwarrior.util import rate_limit



class GithubService(IssueService):
    def __init__(self, *args, **kw):
        super(GithubService, self).__init__(*args, **kw)
        self.ghc = github2.client.Github()

    @rate_limit(limit_amount=60, limit_period=60)
    def pull(self, tag):
        return [(tag, i) for i in self.ghc.issues.list(tag)]

    def get_owner(self, issue):
        # Currently unimplemented for github-proper
        # See validate_config(...) below.
        return None

    def issues(self):
        user = self.config.get(self.target, 'username')

        has_issues = lambda repo: repo.has_issues
        repos = filter(has_issues, self.ghc.repos.list(user))

        issues = sum([self.pull(user + "/" + r.name) for r in repos], [])

        issues = filter(self.include, issues)

        return [{
            "description": self.description(issue.title, issue.html_url),
            "project": tag.split('/')[1],
        } for tag, issue in issues]


    @classmethod
    def validate_config(cls, config, target):
        if not config.has_option(target, 'username'):
            die("[%s] has no 'username'" % target)

        if config.has_option(target, 'only_if_assigned'):
            die("[%s] - github does not currently support issue owners." %
                target)

        IssueService.validate_config(config, target)
