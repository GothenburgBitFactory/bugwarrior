from bugwarrior.config import die


class IssueService(object):
    """ Abstract base class for each service """

    def __init__(self, config, target, shorten):
        self.config = config
        self.target = target
        self.shorten = shorten

    @classmethod
    def validate_config(cls, config, target):
        """ Validate generic options for a particular target """
        # TODO -- general validation
        pass

    def description(self, title, url):
        # TODO -- get the '35' here from the config.
        return "(bw) %s .. %s" % (title[:35], self.shorten(url))

    def issues(self):
        """ Override this to gather issues for each service. """
        print "WARNING --", self.target, "not implemented."
        return []


from github import GithubService
from bitbucket import BitbucketService
from trac import TracService


# Constant dict to be used all around town.
SERVICES = {
    'github': GithubService,
    'bitbucket': BitbucketService,
    'trac': TracService,
}


def aggregate_issues(conf, shorten):
    """ Return all issues from every target.

    Takes a config object and a callable which returns a shortened url.
    """

    targets = [t.strip() for t in conf.get('general', 'targets').split(',')]
    services = [
        SERVICES[conf.get(t, 'service')](conf, t, shorten) for t in targets
    ]
    return sum([service.issues() for service in services], [])
