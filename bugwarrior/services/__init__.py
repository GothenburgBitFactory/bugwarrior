from twiggy import log

import bitlyapi

from bugwarrior.config import die
from bugwarrior.db import MARKUP


class IssueService(object):
    """ Abstract base class for each service """

    def __init__(self, config, target, shorten):
        self.config = config
        self.target = target
        self.shorten = shorten

        log.info("Working on [{0}]", self.target)

    @classmethod
    def validate_config(cls, config, target):
        """ Validate generic options for a particular target """
        # TODO -- general validation
        pass

    def description(self, title, url, number, cls="issue"):
        cls_markup = {
            'issue': 'Is',
            'pull_request': 'PR',
        }
        # TODO -- get the '35' here from the config.
        return "%s%s#%i - %s .. %s" % (
            MARKUP, cls_markup[cls], number,
            title[:35], self.shorten(url)
        )

    def include(self, issue):
        """ Return true if the issue in question should be included """

        # TODO -- evaluate cleaning this up.  It's the ugliest stretch of code
        # in here.

        only_if_assigned, also_unassigned = None, None
        try:
            only_if_assigned = self.config.get(
                self.target, 'only_if_assigned')
        except Exception:
            pass

        try:
            also_unassigned = self.config.getboolean(
                self.target, 'also_unassigned')
        except Exception:
            pass

        if only_if_assigned and also_unassigned:
            return self.get_owner(issue) in [only_if_assigned, None]
        elif only_if_assigned and not also_unassigned:
            return self.get_owner(issue) in [only_if_assigned]
        elif not only_if_assigned and also_unassigned:
            return self.get_owner(issue) in [None]
        elif not only_if_assigned and not also_unassigned:
            return self.get_owner(issue) in [None]
        else:
            pass  # Impossible to get here.

    def issues(self):
        """ Override this to gather issues for each service. """
        raise NotImplementedError

    def get_owner(self, issue):
        """ Override this for filtering on tickets """
        raise NotImplementedError


from github import GithubService
from bitbucket import BitbucketService
from trac import TracService


# Constant dict to be used all around town.
SERVICES = {
    'github': GithubService,
    'bitbucket': BitbucketService,
    'trac': TracService,
}


def aggregate_issues(conf):
    """ Return all issues from every target.

    Takes a config object and a callable which returns a shortened url.
    """

    # By default, we don't shorten URLs
    shorten = lambda url: url

    # Setup bitly shortening callback if creds are specified
    bitly_opts = ['bitly.api_user', 'bitly.api_key']
    if all([conf.has_option('general', opt) for opt in bitly_opts]):
        get_opt = lambda option: conf.get('general', option)
        bitly = bitlyapi.BitLy(
            get_opt('bitly.api_user'),
            get_opt('bitly.api_key')
        )
        shorten = lambda url: bitly.shorten(longUrl=url)['url']

    # Create and call service objects for every target in the config
    targets = [t.strip() for t in conf.get('general', 'targets').split(',')]
    return sum([
        SERVICES[conf.get(t, 'service')](conf, t, shorten).issues()
        for t in targets
    ], [])
