from ConfigParser import NoOptionError
import copy
import os
import re
import warnings
import subprocess

import bitlyapi
import dogpile.cache
import six
from twiggy import log
from taskw import TaskWarriorShellout
from taskw.exceptions import TaskwarriorError

from bugwarrior.config import asbool
from bugwarrior.notifications import send_notification


MARKUP = "(bw)"


DOGPILE_CACHE_PATH = os.path.expanduser('~/.cache/bitly.dbm')
if not os.path.isdir(os.path.dirname(DOGPILE_CACHE_PATH)):
    os.mkdirs(os.path.dirname(DOGPILE_CACHE_PATH))
CACHE_REGION = dogpile.cache.make_region().configure(
    "dogpile.cache.dbm",
    arguments=dict(filename=DOGPILE_CACHE_PATH),
)


# Sentinel value used for aborting processing of tasks
ABORT_PROCESSING = 2


class URLShortener(object):
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(URLShortener, cls).__new__(
                cls, *args, **kwargs
            )
        return cls._instance

    def __init__(self, bitly_user, bitly_key):
        self.bitly_user = bitly_user
        self.bitly_key = bitly_key

        self.bitly = bitlyapi.BitLy(bitly_user, bitly_key)

    @CACHE_REGION.cache_on_arguments()
    def shorten(self, url):
        return self.bitly.shorten(longUrl=url)['url']


class NotFound(Exception):
    pass


class MultipleMatches(Exception):
    pass


def normalize_description(issue_description):
    return issue_description[:issue_description.index(' .. http')]


def get_normalized_annotation(annotation):
    return re.sub(
        r'[\W_]',
        '',
        annotation
    )


def tasks_differ(left, right):
    if set(left) - set(right):
        return True

    all_keys = set(left.keys()) | set(right.keys())
    for k in all_keys:
        # We want to allow the user to locally modify their priority,
        # annotations, etc, without us setting those values back everytime we
        # run... so, ignore these.
        if k in ('annotations', 'urgency', 'priority', ):
            continue

        # If a taskwarrior task has 0 tags, the 'left' value is None.
        # If a bugwarrior remote issue has 0 tags, the 'right' is []
        # Here, we avoid declaring things are different by checking falsiness
        if k in ('tags',):
            if not left.get(k) and not right.get(k):
                continue

        if (
            isinstance(left.get(k), (list, tuple))
            and isinstance(right.get(k), (list, tuple))
        ):
            if set(left.get(k, [])) != set(right.get(k, [])):
                return True
        else:
            if unicode(left.get(k)) != unicode(right.get(k)):
                log.name('db').debug(
                    "%s:%s has changed from '%s' to '%s'." % (
                        left['uuid'],
                        k,
                        left.get(k),
                        right.get(k)
                    )
                )
                return True
    return False


def get_annotation_hamming_distance(left, right):
    left = get_normalized_annotation(left)
    right = get_normalized_annotation(right)
    if len(left) > len(right):
        left = left[0:len(right)]
    elif len(right) > len(left):
        right = right[0:len(left)]
    return hamdist(left, right)


def hamdist(str1, str2):
    """Count the # of differences between equal length strings str1 and str2"""
    diffs = 0
    for ch1, ch2 in zip(str1, str2):
        if ch1 != ch2:
            diffs += 1
    return diffs


def get_managed_task_uuids(tw, key_list, legacy_matching):
    expected_task_ids = set([])
    for keys in key_list.values():
        tasks = tw.filter_tasks({
            'and': [('%s.not' % key, '') for key in keys],
            'or': [
                ('status', 'pending'),
                ('status', 'waiting'),
            ],
        })
        expected_task_ids = expected_task_ids | set([
            task['uuid'] for task in tasks
        ])

    if legacy_matching:
        starts_with_markup = tw.filter_tasks({
            'description.startswith': MARKUP,
            'or': [
                ('status', 'pending'),
                ('status', 'waiting'),
            ],
        })
        expected_task_ids = expected_task_ids | set([
            task['uuid'] for task in starts_with_markup
        ])

    return expected_task_ids


def find_local_uuid(tw, keys, issue, legacy_matching=True):
    """ For a given issue issue, find its local UUID.

    Assembles a list of task IDs existing in taskwarrior
    matching the supplied issue (`issue`) on the combination of any
    set of supplied unique identifiers (`keys`) or, optionally,
    the task's description field (should `legacy_matching` be `True`).

    :params:
    * `tw`: An instance of `taskw.TaskWarriorShellout`
    * `keys`: A list of lists of keys to use for uniquely identifying
      an issue.  To clarify the "list of lists" behavior, assume that
      there are two services, one having a single primary key field
      -- 'serviceAid' -- and another having a pair of fields composing
      its primary key -- 'serviceBproject' and 'serviceBnumber' --, the
      incoming data for this field would be::

        [
            ['serviceAid'],
            ['serviceBproject', 'serviceBnumber'],
        ]

    * `issue`: A instance of a subclass of `bugwarrior.services.Issue`.
    * `legacy_matching`: By default, this is enabled, and it allows
      the matching algorithm to -- in addition to searching by stored
      issue keys -- search using the task's description for a match.

    :returns:
    * A single string UUID.

    :raises:
    * `bugwarrior.db.MultipleMatches`: if multiple matches were found.
    * `bugwarrior.db.NotFound`: if an issue was not found.

    """
    if not issue['description']:
        raise ValueError('Issue %s has no description.' % issue)

    possibilities = set([])

    if legacy_matching:
        legacy_description = issue.get_default_description().rsplit('..', 1)[0]
        results = tw.filter_tasks({
            'description.startswith': legacy_description,
            'or': [
                ('status', 'pending'),
                ('status', 'waiting'),
            ],
        })
        possibilities = possibilities | set([
            task['uuid'] for task in results
        ])

    for service, key_list in six.iteritems(keys):
        if any([key in issue for key in key_list]):
            results = tw.filter_tasks({
                'and': [(key, issue[key]) for key in key_list],
                'or': [
                    ('status', 'pending'),
                    ('status', 'waiting'),
                ],
            })
            possibilities = possibilities | set([
                task['uuid'] for task in results
            ])

    if len(possibilities) == 1:
        return possibilities.pop()

    if len(possibilities) > 1:
        raise MultipleMatches(
            "Issue %s matched multiple IDs: %s" % (
                issue['description'],
                possibilities
            )
        )

    raise NotFound(
        "No issue was found matching %s" % issue
    )


def merge_annotations(remote_issue, local_task):
    """ Merge annotations from the local task into the remote issue dict

    If there are new annotations in the remote issue that do not appears in the
    local task, additionally return True signalling that the new remote
    annotations should be synched to the db.
    """

    # Ensure that empty defaults are present
    remote_issue['annotations'] = remote_issue.get('annotations', [])
    local_task['annotations'] = local_task.get('annotations', [])

    # Setup some shorthands
    remote_annotations = [a for a in remote_issue['annotations']]
    local_annotations = [a['description'] for a in local_task['annotations']]

    # Do two things.
    # * If a local does not appears in remote, then add it there so users can
    #   maintain their own list of locals.
    # * If a remote does not appear in local, then return True

    # Part 1
    for local in local_annotations:
        for remote in remote_annotations:
            if get_annotation_hamming_distance(remote, local) == 0:
                remote_issue['annotations'].append(local)
                break

    # Part 2
    for remote in remote_annotations:
        found = False
        for local in local_annotations:
            if get_annotation_hamming_distance(remote, local) == 0:
                found = True
                break

        # Then we have a new remote annotation that should be synced locally.
        if not found:
            log.name('db').debug(
                "%s not found in %r" % (remote, local_annotations))
            return True

    # Otherwise, we found all of our remotes in our local annotations.
    return False


def synchronize(issue_generator, conf):

    def _bool_option(section, option, default):
        try:
            return section in conf.sections() and \
                asbool(conf.get(section, option, default))
        except NoOptionError:
            return default

    targets = [t.strip() for t in conf.get('general', 'targets').split(',')]
    services = set([conf.get(target, 'service') for target in targets])
    key_list = build_key_list(services)
    uda_list = build_uda_list(services)
    if uda_list:
        log.name('bugwarrior').info(
            'Service-defined UDAs (you can optionally add these to your '
            '~/.taskrc for use in reports):'
        )
        for uda in uda_list:
            log.name('bugwarrior').info('%s=%s' % uda)

    notify = _bool_option('notifications', 'notifications', 'False')

    path = '~/.taskrc'
    if conf.has_option('general', 'taskrc'):
        path = conf.get('general', 'taskrc')

    tw = TaskWarriorShellout(
        config_filename=path,
        config_overrides=dict(uda_list)
    )

    legacy_matching = _bool_option('general', 'legacy_matching', 'True')

    issue_updates = {
        'new': [],
        'existing': [],
        'changed': [],
        'closed': get_managed_task_uuids(tw, key_list, legacy_matching),
    }

    # Before running CRUD operations, call the pre_import hook(s).
    if conf.has_option('hooks', 'pre_import'):
        pre_import = [t.strip() for t in conf.get('hooks', 'pre_import').split(',')]
        if pre_import is not None:
            for hook in pre_import:
                exit_code = subprocess.call(hook, shell=True)
                if exit_code is not 0:
                    log.name('hooks:pre_import').error(
                            'Non-zero exit code %d on hook %s' % (exit_code, hook))
                    sys.exit(1)

    for issue in issue_generator:
        if isinstance(issue, tuple) and issue[0] == ABORT_PROCESSING:
            raise RuntimeError(issue[1])
        try:
            existing_uuid = find_local_uuid(
                tw, key_list, issue, legacy_matching=legacy_matching
            )
            issue_dict = dict(issue)
            _, task = tw.get_task(uuid=existing_uuid)
            task_copy = copy.deepcopy(task)


            annotations_changed = merge_annotations(issue_dict, task)

            if annotations_changed:
                log.name('db').debug("%s annotations changed." % existing_uuid)

            # Merging tags, too
            for tag in task.get('tags', []):
                if not 'tags' in issue_dict:
                    issue_dict['tags'] = []
                if tag not in issue_dict['tags']:
                    issue_dict['tags'].append(tag)

            task.update(issue_dict)
            if tasks_differ(task_copy, task) or annotations_changed:
                issue_updates['changed'].append(task)
            else:
                issue_updates['existing'].append(task)

            if existing_uuid in issue_updates['closed']:
                issue_updates['closed'].remove(existing_uuid)

        except MultipleMatches as e:
            log.name('db').error("Multiple matches: {0}", six.text_type(e))
            log.name('db').trace(e)
        except NotFound:
            issue_updates['new'].append(dict(issue))

    # Add new issues
    log.name('db').info("Adding {0} tasks", len(issue_updates['new']))
    for issue in issue_updates['new']:
        log.name('db').info(
            "Adding task {0}",
            issue['description'].encode("utf-8")
        )
        if notify:
            send_notification(issue, 'Created', conf)

        try:
            tw.task_add(**issue)
        except TaskwarriorError as e:
            log.name('db').trace(e)

    log.name('db').info("Updating {0} tasks", len(issue_updates['changed']))
    for issue in issue_updates['changed']:
        log.name('db').info(
            "Updating task {0}",
            issue['description'].encode("utf-8")
        )
        try:
            tw.task_update(issue)
        except TaskwarriorError as e:
            log.name('db').trace(e)

    log.name('db').info("Closing {0} tasks", len(issue_updates['closed']))
    for issue in issue_updates['closed']:
        _, task_info = tw.get_task(uuid=issue)
        log.name('db').info(
            "Completing task {0} {1}",
            task_info['uuid'],
            task_info['description'],
        )
        if notify:
            send_notification(task_info, 'Completed', conf)

        try:
            tw.task_done(uuid=issue)
        except TaskwarriorError as e:
            log.name('db').trace(e)

    # Send notifications
    if notify:
        send_notification(
            dict(
                description="New: %d, Changed: %d, Completed: %d" % (
                    len(issue_updates['new']),
                    len(issue_updates['changed']),
                    len(issue_updates['closed'])
                )
            ),
            'bw_finished',
            conf,
        )


def build_key_list(targets):
    from bugwarrior.services import SERVICES

    keys = {}
    for target in targets:
        keys[target] = SERVICES[target].ISSUE_CLASS.UNIQUE_KEY
    return keys


def build_uda_list(targets):
    """ Returns a list of UDAs defined by given targets

    For all targets in `targets`, build a list of 2-tuples representing
    the UDAs defined by the passed-in services (`targets`).

    Given a hypothetical situation in which you have two services, the first
    of which defining a UDA named 'serviceAid' ("Service A ID", string) and
    a second service defining two UDAs named 'serviceBproject'
    ("Service B Project", string) and 'serviceBnumber'
    ("Service B Number", numeric), this would return the following structure::

        [
            ('uda.serviceAid.label', 'Service A ID'),
            ('uda.serviceAid.type', 'string'),
            ('uda.serviceBid.label', 'Service B Project'),
            ('uda.serviceBid.type', 'string'),
            ('uda.serviceBnumber.label', 'Service B Number'),
            ('uda.serviceBnumber.type', 'numeric'),
        ]


    """

    from bugwarrior.services import SERVICES

    uda_output = []
    targets_udas = {}
    for target in targets:
        targets_udas.update(SERVICES[target].ISSUE_CLASS.UDAS)
    for name, uda_attributes in six.iteritems(targets_udas):
        for attrib, value in six.iteritems(uda_attributes):
            if '_' in name:
                warnings.warn(
                    "Service '%s' has defined a potentially invalid UDA "
                    "named '%s'.  As of the time of this writing, UDAs "
                    "must be alphanumeric, and may not contain "
                    "underscores." % (
                        target,
                        name,
                    ),
                    RuntimeWarning
                )
            uda_output.append(
                (
                    'uda.%s.%s' % (name, attrib, ),
                    '%s' % (value, ),
                )
            )
    return sorted(uda_output)
