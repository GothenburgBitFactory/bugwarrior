import copy
import multiprocessing
import time

from dateutil.parser import parse as parse_date
from dateutil.tz import tzlocal
from jinja2 import Template
import pytz
import six
from twiggy import log

from taskw.task import Task

from bugwarrior.utils import DeferredImportingDict
from bugwarrior.config import asbool
from bugwarrior.db import MARKUP, URLShortener, ABORT_PROCESSING


# Sentinels for process completion status
SERVICE_FINISHED_OK = 0
SERVICE_FINISHED_ERROR = 1

# Used by `parse_date` as a timezone when you would like a naive
# date string to be parsed as if it were in your local timezone
LOCAL_TIMEZONE = 'LOCAL_TIMEZONE'

# Constant dict to be used all around town.
# It will defer actually importing a service until someone tries to access it
# in the dict.  This should help expose odd ImportErrors in a more obvious way
# for end users.  See https://github.com/ralphbean/bugwarrior/issues/132
SERVICES = DeferredImportingDict({
    'github':        'bugwarrior.services.github:GithubService',
    'gitlab':        'bugwarrior.services.gitlab:GitlabService',
    'bitbucket':     'bugwarrior.services.bitbucket:BitbucketService',
    'trac':          'bugwarrior.services.trac:TracService',
    'bugzilla':      'bugwarrior.services.bz:BugzillaService',
    'teamlab':       'bugwarrior.services.teamlab:TeamLabService',
    'redmine':       'bugwarrior.services.redmine:RedMineService',
    'activecollab2': 'bugwarrior.services.activecollab2:ActiveCollab2Service',
    'activecollab':  'bugwarrior.services.activecollab:ActiveCollabService',
    'jira':          'bugwarrior.services.jira:JiraService',
    'megaplan':      'bugwarrior.services.megaplan:MegaplanService',
    'phabricator':   'bugwarrior.services.phabricator:PhabricatorService',
    'versionone':    'bugwarrior.services.versionone:VersionOneService',
})


class IssueService(object):
    """ Abstract base class for each service """
    # Which class should this service instantiate for holding these issues?
    ISSUE_CLASS = None
    # What prefix should we use for this service's configuration values
    CONFIG_PREFIX = ''

    def __init__(self, config, main_section, target):
        self.config = config
        self.main_section = main_section
        self.target = target

        self.desc_len = 35
        if config.has_option(self.main_section, 'description_length'):
            self.desc_len = self.config.getint(self.main_section, 'description_length')

        self.anno_len = 45
        if config.has_option(self.main_section, 'annotation_length'):
            self.anno_len = self.config.getint(self.main_section, 'annotation_length')

        self.inline_links = True
        if config.has_option(self.main_section, 'inline_links'):
            self.inline_links = asbool(config.get(self.main_section, 'inline_links'))

        self.annotation_links = not self.inline_links
        if config.has_option(self.main_section, 'annotation_links'):
            self.annotation_links = asbool(
                config.get(self.main_section, 'annotation_links')
            )

        self.shorten = False
        if config.has_option(self.main_section, 'shorten'):
            self.shorten = asbool(config.get(self.main_section, 'shorten'))

        self.add_tags = []
        if config.has_option(self.target, 'add_tags'):
            for raw_option in self.config.get(
                self.target, 'add_tags'
            ).split(','):
                option = raw_option.strip(' +;')
                if option:
                    self.add_tags.append(option)

        self.default_priority = 'M'
        if config.has_option(self.target, 'default_priority'):
            self.default_priority = config.get(self.target, 'default_priority')

        log.name(target).info("Working on [{0}]", self.target)

    def get_templates(self):
        """ Get any defined templates for configuration values.

        Users can override the value of any Taskwarrior field using
        this feature on a per-key basis.  The key should be the name of
        the field to you would like to configure the value of, followed
        by '_template', and the value should be a Jinja template
        generating the field's value.  As context variables, all fields
        on the taskwarrior record are available.

        For example, to prefix the returned
        project name for tickets returned by a service with 'workproject_',
        you could add an entry reading:

            project_template = workproject_{{project}}

        Or, if you'd simply like to override the returned project name
        for all tickets incoming from a specific service, you could add
        an entry like:

            project_template = myprojectname

        The above would cause all issues to recieve a project name
        of 'myprojectname', regardless of what the project name of the
        generated issue was.

        """
        templates = {}
        for key in six.iterkeys(Task.FIELDS):
            template_key = '%s_template' % key
            if self.config.has_option(self.target, template_key):
                templates[key] = self.config.get(self.target, template_key)
        return templates

    def config_get_default(self, key, default=None, to_type=None):
        try:
            return self.config_get(key, to_type=to_type)
        except:
            return default

    def config_get(self, key=None, to_type=None):
        value = self.config.get(self.target, self._get_key(key))
        if to_type:
            return to_type(value)
        return value

    @classmethod
    def _get_key(cls, key):
        return '%s.%s' % (cls.CONFIG_PREFIX, key)

    def get_service_metadata(self):
        return {}

    def get_issue_for_record(self, record, extra=None):
        origin = {
            'annotation_length': self.anno_len,
            'default_priority': self.default_priority,
            'description_length': self.desc_len,
            'templates': self.get_templates(),
            'target': self.target,
            'shorten': self.shorten,
            'inline_links': self.inline_links,
            'add_tags': self.add_tags,
        }
        origin.update(self.get_service_metadata())
        return self.ISSUE_CLASS(record, origin=origin, extra=extra)

    def build_annotations(self, annotations, url):
        final = []
        if self.annotation_links:
            final.append(url)
        for author, message in annotations:
            message = message.strip()
            if not message or not author:
                continue
            message = message.replace('\n', '').replace('\r', '')
            final.append(
                '@%s - %s%s' % (
                    author,
                    message[0:self.anno_len],
                    '...' if len(message) > self.anno_len else ''
                )
            )
        return final

    @classmethod
    def validate_config(cls, config, target):
        """ Validate generic options for a particular target """
        pass

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

    def get_owner(self, issue):
        """ Override this for filtering on tickets """
        raise NotImplementedError()

    def issues(self):
        """ Returns a list of dicts representing issues from a remote service.

        This is the main place to begin if you are implementing a new service
        for bugwarrior.  Override this to gather issues for each service.

        Each item in the list should be a dict that looks something like this:

            {
                "description": "Some description of the issue",
                "project": "some_project",
                "priority": "H",
                "annotations": [
                    "This is an annotation",
                    "This is another annotation",
                ]
            }


        The description can be 'anything' but must be consistent and unique for
        issues you're pulling from a remote service.  You can and should use
        the ``.description(...)`` method to help format your descriptions.

        The project should be a string and may be anything you like.

        The priority should be one of "H", "M", or "L".
        """
        raise NotImplementedError()

    @classmethod
    def get_keyring_service(cls, config, section):
        """ Given the keyring service name for this service. """
        raise NotImplementedError


class Issue(object):
    # Set to a dictionary mapping UDA short names with type and long name.
    #
    # Example::
    #
    #     {
    #         'project_id': {
    #             'type': 'string',
    #             'label': 'Project ID',
    #         },
    #         'ticket_number': {
    #             'type': 'number',
    #             'label': 'Ticket Number',
    #         },
    #     }
    #
    # Note: For best results, dictionary keys should be unique!
    UDAS = {}
    # Should be a tuple of field names (can be UDA names) that are usable for
    # uniquely identifying an issue in the foreign system.
    UNIQUE_KEY = []
    # Should be a dictionary of value-to-level mappings between the foreign
    # system and the string values 'H', 'M' or 'L'.
    PRIORITY_MAP = {}

    def __init__(self, foreign_record, origin=None, extra=None):
        self._foreign_record = foreign_record
        self._origin = origin if origin else {}
        self._extra = extra if extra else {}

    def update_extra(self, extra):
        self._extra.update(extra)

    def to_taskwarrior(self):
        """ Transform a foreign record into a taskwarrior dictionary."""
        raise NotImplementedError()

    def get_default_description(self):
        """ Return the old-style verbose description from bugwarrior.

        This is useful for two purposes:

        * Finding and linking historically-created records.
        * Allowing people to keep using the historical description
          for taskwarrior.

        """
        raise NotImplementedError()

    def get_added_tags(self):
        added_tags = []
        for tag in self.origin['add_tags']:
            tag = Template(tag).render(self.get_template_context())
            if tag:
                added_tags.append(tag)

        return added_tags

    def get_taskwarrior_record(self, refined=True):
        if not getattr(self, '_taskwarrior_record', None):
            self._taskwarrior_record = self.to_taskwarrior()
        record = copy.deepcopy(self._taskwarrior_record)
        if refined:
            record = self.refine_record(record)
        if not 'tags' in record:
            record['tags'] = []
        if refined:
            record['tags'].extend(self.get_added_tags())
        return record

    def get_priority(self):
        return self.PRIORITY_MAP.get(
            self.record.get('priority'),
            self.origin['default_priority']
        )

    def get_processed_url(self, url):
        """ Returns a URL with conditional processing.

        If the following config key are set:

        - [general]shorten

        returns a shortened URL; otherwise returns the URL unaltered.

        """
        if self.origin['shorten']:
            return URLShortener().shorten(url)
        return url

    def parse_date(self, date, timezone='UTC'):
        """ Parse a date string into a datetime object.

        :param `date`: A time string parseable by `dateutil.parser.parse`
        :param `timezone`: The string timezone name (from `pytz.all_timezones`)
            to use as a default should the parsed time string not include
            timezone information.

        """
        if date:
            date = parse_date(date)
            if not date.tzinfo:
                if timezone == LOCAL_TIMEZONE:
                    tzinfo = tzlocal()
                else:
                    tzinfo = pytz.timezone(timezone)
                date = date.replace(tzinfo=tzinfo)
            return date
        return None

    def build_default_description(
        self, title='', url='', number='', cls="issue"
    ):
        cls_markup = {
            'issue': 'Is',
            'pull_request': 'PR',
            'merge_request': 'MR',
            'task': '',
            'subtask': 'Subtask #',
        }
        url_separator = ' .. '
        url = url if self.origin['inline_links'] else ''
        return "%s%s#%s - %s%s%s" % (
            MARKUP,
            cls_markup[cls],
            number,
            title[:self.origin['description_length']],
            url_separator if url else '',
            url,
        )

    def _get_unique_identifier(self):
        record = self.get_taskwarrior_record()
        return dict([
            (key, record[key],) for key in self.UNIQUE_KEY
        ])

    def get_template_context(self):
        context = (
            self.get_taskwarrior_record(refined=False).copy()
        )
        context.update(self.extra)
        context.update({
            'description': self.get_default_description(),
        })
        return context

    def refine_record(self, record):
        for field in six.iterkeys(Task.FIELDS):
            if field in self.origin['templates']:
                template = Template(self.origin['templates'][field])
                record[field] = template.render(self.get_template_context())
            elif hasattr(self, 'get_default_%s' % field):
                record[field] = getattr(self, 'get_default_%s' % field)()
        return record

    def __iter__(self):
        record = self.get_taskwarrior_record()
        for key in six.iterkeys(record):
            yield key

    def keys(self):
        return list(self.__iter__())

    def iterkeys(self):
        return self.__iter__()

    def items(self):
        record = self.get_taskwarrior_record()
        return list(six.iteritems(record))

    def iteritems(self):
        record = self.get_taskwarrior_record()
        for item in six.iteritems(record):
            yield item

    def update(self, *args):
        raise AttributeError(
            "You cannot set attributes on issues."
        )

    def get(self, attribute, default=None):
        try:
            return self[attribute]
        except KeyError:
            return default

    def __getitem__(self, attribute):
        record = self.get_taskwarrior_record()
        return record[attribute]

    def __setitem__(self, attribute, value):
        raise AttributeError(
            "You cannot set attributes on issues."
        )

    def __delitem__(self, attribute):
        raise AttributeError(
            "You cannot delete attributes from issues."
        )

    @property
    def record(self):
        return self._foreign_record

    @property
    def extra(self):
        return self._extra

    @property
    def origin(self):
        return self._origin

    def __unicode__(self):
        return '%s: %s' % (
            self.origin['target'],
            self.get_taskwarrior_record()['description']
        )

    def __str__(self):
        return self.__unicode__().encode('ascii', 'replace')

    def __repr__(self):
        return '<%s>' % self.__unicode__()


def _aggregate_issues(conf, main_section, target, queue, service_name):
    """ This worker function is separated out from the main
    :func:`aggregate_issues` func only so that we can use multiprocessing
    on it for speed reasons.
    """

    start = time.time()

    try:
        service = SERVICES[service_name](conf, main_section, target)
        issue_count = 0
        for issue in service.issues():
            queue.put(issue)
            issue_count += 1
    except Exception as e:
        log.name(target).trace('error').critical(
            "Worker for [%s] failed: %s" % (target, e)
        )
        queue.put(
            (SERVICE_FINISHED_ERROR, (target, e))
        )
    else:
        queue.put(
            (SERVICE_FINISHED_OK, (target, issue_count, ))
        )
    finally:
        duration = time.time() - start
        log.name(target).info("Done with [%s] in %fs" % (target, duration))


def aggregate_issues(conf, main_section):
    """ Return all issues from every target. """
    log.name('bugwarrior').info("Starting to aggregate remote issues.")

    # Create and call service objects for every target in the config
    targets = [t.strip() for t in conf.get(main_section, 'targets').split(',')]

    queue = multiprocessing.Queue()

    log.name('bugwarrior').info("Spawning %i workers." % len(targets))
    processes = []

    if (
        conf.has_option(main_section, 'development')
        and asbool(conf.get(main_section, 'development'))
    ):
        for target in targets:
            _aggregate_issues(
                conf,
                main_section,
                target,
                queue,
                conf.get(target, 'service')
            )
    else:
        for target in targets:
            proc = multiprocessing.Process(
                target=_aggregate_issues,
                args=(conf, main_section, target, queue, conf.get(target, 'service'))
            )
            proc.start()
            processes.append(proc)

            # Sleep for 1 second here to try and avoid a race condition where
            # all N workers start up and ask the gpg-agent process for
            # information at the same time.  This causes gpg-agent to fumble
            # and tell some of our workers some incomplete things.
            time.sleep(1)

    currently_running = len(targets)
    while currently_running > 0:
        issue = queue.get(True)
        if isinstance(issue, tuple):
            completion_type, args = issue
            if completion_type == SERVICE_FINISHED_ERROR:
                target, e = args
                for process in processes:
                    process.terminate()
                yield ABORT_PROCESSING, e
            currently_running -= 1
            continue
        yield issue

    log.name('bugwarrior').info("Done aggregating remote issues.")
