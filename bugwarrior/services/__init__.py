from twiggy import log

import bitlyapi
import time
import os
import dogpile.cache

from bugwarrior.config import die, asbool
from bugwarrior.db import MARKUP


class IssueService(object):
    """ Abstract base class for each service """

    def __init__(self, config, target, shorten):
        self.config = config
        self.target = target
        self.shorten = shorten
        if config.has_option('general', 'description_length'):
            self.desc_len = self.config.getint('general', 'description_length')
        else:
            self.desc_len = 35
        if config.has_option('general', 'annotation_length'):
            self.anno_len = self.config.getint('general', 'annotation_length')
        else:
            self.anno_len = 45
        log.name(target).info("Working on [{0}]", self.target)

    @classmethod
    def validate_config(cls, config, target):
        """ Validate generic options for a particular target """

        cls.default_priority = 'M'
        if config.has_option(target, 'default_priority'):
            cls.default_priority = config.get(target, 'default_priority')

    def format_annotation(self, created, user, body):
        if not body:
            body = ''
        body = body.replace('\n', '').replace('\r', '')[:self.anno_len]
        return (
            "annotation_%i" % time.mktime(created.timetuple()),
            "@%s - %s..." % (user, body),
        )

    def description(self, title, url, number, cls="issue"):
        cls_markup = {
            'issue': 'Is',
            'pull_request': 'PR',
        }
        return "%s%s#%s - %s .. %s" % (
            MARKUP, cls_markup[cls], str(number),
            title[:self.desc_len], self.shorten(url)
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
            return True
        elif not only_if_assigned and not also_unassigned:
            return True
        else:
            pass  # Impossible to get here.

    def issues(self):
        """ Returns a list of dicts representing issues from a remote service.

        This is the main place to begin if you are implementing a new service
        for bugwarrior.  Override this to gather issues for each service.

        Each item in the list should be a dict that looks something like this:

            {
                "description": "Some description of the issue",
                "project": "some_project",
                "priority": "H",
                "annotation_1357787477": "This is an annotation",
                "annotation_1357787500": "This is another annotation",
            }


        The description can be 'anything' but must be consistent and unique for
        issues you're pulling from a remote service.  You can and should use
        the ``.description(...)`` method to help format your descriptions.

        The project should be a string and may be anything you like.

        The priority should be one of "H", "M", or "L".

        Annotations are a little more tricky; the *key* for an annotation is
        composed of the string "annotation_" followed by a UNIX timestamp like
        "annotation_1357787477".  The associated value is the value of the
        annotation dated at that time.  This is intended to be used with
        "comments" on remote ticketing systems so that an initial bug report
        can be followed up with by multiple, dated annotations.

        You can and should use the ``.format_annotation(...)`` method to help
        format your annotations.
        """
        raise NotImplementedError

    def get_owner(self, issue):
        """ Override this for filtering on tickets """
        raise NotImplementedError


from github import GithubService
from bitbucket import BitbucketService
from trac import TracService
from bz import BugzillaService
from teamlab import TeamLabService
from redmine import RedMineService
from jira import JiraService
from activecollab2 import ActiveCollab2Service
from activecollab3 import ActiveCollab3Service


# Constant dict to be used all around town.
SERVICES = {
    'github': GithubService,
    'bitbucket': BitbucketService,
    'trac': TracService,
    'bugzilla': BugzillaService,
    'teamlab': TeamLabService,
    'redmine': RedMineService,
    'jira': JiraService,
    'activecollab2': ActiveCollab2Service,
    'activecollab3': ActiveCollab3Service,
}


try:
    from mplan import MegaplanService
    SERVICES['megaplan'] = MegaplanService
except ImportError:
    pass

WORKER_FAILURE = "__this signifies a worker failure__"


def _aggregate_issues(args):
    """ This worker function is separated out from the main
    :func:`aggregate_issues` func only so that we can use multiprocessing
    on it for speed reasons.
    """

    # Unpack arguments
    conf, target = args

    try:
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

            cachefile = os.path.expanduser("~/.cache/bitly.dbm")
            if not os.path.isdir(os.path.expanduser("~/.cache/")):
                os.makedirs(os.path.expanduser("~/.cache/"))

            # Cache in order to avoid hitting the bitly api over and over.
            # bitly links never expire or change, so why not cache on disk?
            region = dogpile.cache.make_region().configure(
                "dogpile.cache.dbm",
                arguments=dict(filename=cachefile),
            )
            shorten = region.cache_on_arguments()(shorten)

        service = SERVICES[conf.get(target, 'service')](conf, target, shorten)
        return service.issues()
    except Exception as e:
        log.name(target).trace('error').critical("worker failure")
        return WORKER_FAILURE
    finally:
        log.name(target).info("Done with [%s]" % target)

# Import here so that mproc knows about _aggregate_issues
import multiprocessing


def aggregate_issues(conf):
    """ Return all issues from every target.

    Takes a config object and a callable which returns a shortened url.
    """
    log.name('bugwarrior').info("Starting to aggregate remote issues.")

    # Create and call service objects for every target in the config
    targets = [t.strip() for t in conf.get('general', 'targets').split(',')]

    # This multiprocessing stuff is kind of experimental.
    use_multiprocessing = conf.has_option('general', 'multiprocessing') and \
        asbool(conf.get('general', 'multiprocessing'))

    if use_multiprocessing:
        log.name('bugwarrior').info("Spawning %i workers." % len(targets))
        pool = multiprocessing.Pool(processes=len(targets))
        map_function = pool.map
    else:
        log.name('bugwarrior').info("Processing targets in serial.")
        map_function = map

    issues_by_target = map_function(
        _aggregate_issues,
        zip([conf] * len(targets), targets)
    )
    log.name('bugwarrior').info("Done aggregating remote issues.")
    if WORKER_FAILURE in issues_by_target:
        log.name('bugwarrior').critical("A worker failed.  Aborting.")
        raise RuntimeError('Worker failure')
    return sum(issues_by_target, [])
