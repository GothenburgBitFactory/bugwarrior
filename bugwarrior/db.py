from __future__ import unicode_literals
from future import standard_library
standard_library.install_aliases()
from builtins import zip
from builtins import object

from configparser import NoOptionError, NoSectionError
import os
import re
import subprocess

import requests
import dogpile.cache
import six
from taskw import TaskWarriorShellout
from taskw.exceptions import TaskwarriorError

from bugwarrior.config import asbool, get_taskrc_path
from bugwarrior.notifications import send_notification

import logging
log = logging.getLogger(__name__)


MARKUP = "(bw)"


DOGPILE_CACHE_PATH = os.path.expanduser(
    os.getenv('XDG_CACHE_HOME', '~/.cache') + '/dagd.dbm')

if not os.path.isdir(os.path.dirname(DOGPILE_CACHE_PATH)):
    os.makedirs(os.path.dirname(DOGPILE_CACHE_PATH))
CACHE_REGION = dogpile.cache.make_region().configure(
    "dogpile.cache.dbm",
    arguments=dict(filename=DOGPILE_CACHE_PATH),
)


class URLShortener(object):
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(URLShortener, cls).__new__(
                cls, *args, **kwargs
            )
        return cls._instance

    @CACHE_REGION.cache_on_arguments()
    def shorten(self, url):
        if not url:
            return ''
        base = 'https://da.gd/s'
        return requests.get(base, params=dict(url=url)).text.strip()


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
        six.text_type(annotation)
    )


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
    for keys in list(key_list.values()):
        tasks = tw.filter_tasks({
            'and': [('%s.any' % key, None) for key in keys],
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


def find_local_uuid(tw, keys, issue, legacy_matching=False):
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

    * `issue`: An instance of a subclass of `bugwarrior.services.Issue`.
    * `legacy_matching`: By default, this is disabled, and it allows
      the matching algorithm to -- in addition to searching by stored
      issue keys -- search using the task's description for a match.
      It is prone to error and should avoided if possible.

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
        # Furthermore, we have to kill off any single quotes which break in
        # task-2.4.x, as much as it saddens me.
        legacy_description = legacy_description.split("'")[0]
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
                'and': [("%s.is" % key, issue[key]) for key in key_list],
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


def merge_left(field, local_task, remote_issue, hamming=False):
    """ Merge array field from the remote_issue into local_task

    * Local 'left' entries are preserved without modification
    * Remote 'left' are appended to task if not present in local.

    :param `field`: Task field to merge.
    :param `local_task`: `taskw.task.Task` object into which to merge
        remote changes.
    :param `remote_issue`: `dict` instance from which to merge into
        local task.
    :param `hamming`: (default `False`) If `True`, compare entries by
        truncating to maximum length, and comparing hamming distances.
        Useful generally only for annotations.

    """

    # Ensure that empty defaults are present
    local_field = local_task.get(field, [])
    remote_field = remote_issue.get(field, [])

    # We need to make sure an array exists for this field because
    # we will be appending to it in a moment.
    if field not in local_task:
        local_task[field] = []

    # If a remote does not appear in local, add it to the local task
    new_count = 0
    for remote in remote_field:
        found = False
        for local in local_field:
            if (
                # For annotations, they don't have to match *exactly*.
                (
                    hamming
                    and get_annotation_hamming_distance(remote, local) == 0
                )
                # But for everything else, they should.
                or (
                    remote == local
                )
            ):
                found = True
                break
        if not found:
            log.debug("%s not found in %r" % (remote, local_field))
            local_task[field].append(remote)
            new_count += 1
    if new_count > 0:
        log.debug('Added %s new values to %s (total: %s)' % (
            new_count, field, len(local_task[field]),))


def run_hooks(conf, name):
    if conf.has_option('hooks', name):
        pre_import = [
            t.strip() for t in conf.get('hooks', name).split(',')
        ]
        if pre_import is not None:
            for hook in pre_import:
                exit_code = subprocess.call(hook, shell=True)
                if exit_code is not 0:
                    msg = 'Non-zero exit code %d on hook %s' % (
                        exit_code, hook
                    )
                    log.error(msg)
                    raise RuntimeError(msg)


def synchronize(issue_generator, conf, main_section, dry_run=False):
    def _bool_option(section, option, default):
        try:
            return asbool(conf.get(section, option))
        except (NoSectionError, NoOptionError):
            return default

    targets = [t.strip() for t in conf.get(main_section, 'targets').split(',')]
    services = set([conf.get(target, 'service') for target in targets])
    key_list = build_key_list(services)
    uda_list = build_uda_config_overrides(services)

    if uda_list:
        log.info(
            'Service-defined UDAs exist: you can optionally use the '
            '`bugwarrior-uda` command to export a list of UDAs you can '
            'add to your taskrc file.'
        )

    static_fields = static_fields_default = ['priority']
    if conf.has_option(main_section, 'static_fields'):
        static_fields = conf.get(main_section, 'static_fields').split(',')

    # Before running CRUD operations, call the pre_import hook(s).
    run_hooks(conf, 'pre_import')

    notify = _bool_option('notifications', 'notifications', False) and not dry_run

    tw = TaskWarriorShellout(
        config_filename=get_taskrc_path(conf, main_section),
        config_overrides=uda_list,
        marshal=True,
    )

    legacy_matching = _bool_option(main_section, 'legacy_matching', False)
    merge_annotations = _bool_option(main_section, 'merge_annotations', True)
    merge_tags = _bool_option(main_section, 'merge_tags', True)

    issue_updates = {
        'new': [],
        'existing': [],
        'changed': [],
        'closed': get_managed_task_uuids(tw, key_list, legacy_matching),
    }

    for issue in issue_generator:
        try:
            existing_uuid = find_local_uuid(
                tw, key_list, issue, legacy_matching=legacy_matching
            )
            issue_dict = dict(issue)
            _, task = tw.get_task(uuid=existing_uuid)

            # Drop static fields from the upstream issue.  We don't want to
            # overwrite local changes to fields we declare static.
            for field in static_fields:
                del issue_dict[field]

            # Merge annotations & tags from online into our task object
            if merge_annotations:
                merge_left('annotations', task, issue_dict, hamming=True)

            if merge_tags:
                merge_left('tags', task, issue_dict)

            issue_dict.pop('annotations', None)
            issue_dict.pop('tags', None)

            task.update(issue_dict)

            if task.get_changes(keep=True):
                issue_updates['changed'].append(task)
            else:
                issue_updates['existing'].append(task)

            if existing_uuid in issue_updates['closed']:
                issue_updates['closed'].remove(existing_uuid)

        except MultipleMatches as e:
            log.exception("Multiple matches: %s", six.text_type(e))
        except NotFound:
            issue_updates['new'].append(dict(issue))

    notreally = ' (not really)' if dry_run else ''
    # Add new issues
    log.info("Adding %i tasks", len(issue_updates['new']))
    for issue in issue_updates['new']:
        log.info("Adding task %s%s",
            issue['description'], notreally)
        if dry_run:
            continue
        if notify:
            send_notification(issue, 'Created', conf)

        try:
            tw.task_add(**issue)
        except TaskwarriorError as e:
            log.exception("Unable to add task: %s" % e.stderr)

    log.info("Updating %i tasks", len(issue_updates['changed']))
    for issue in issue_updates['changed']:
        changes = '; '.join([
            '{field}: {f} -> {t}'.format(
                field=field,
                f=repr(ch[0]),
                t=repr(ch[1])
            )
            for field, ch in six.iteritems(issue.get_changes(keep=True))
        ])
        log.info(
            "Updating task %s, %s; %s%s",
            six.text_type(issue['uuid']),
            issue['description'],
            changes,
            notreally
        )
        if dry_run:
            continue

        try:
            tw.task_update(issue)
        except TaskwarriorError as e:
            log.exception("Unable to modify task: %s" % e.stderr)

    log.info("Closing %i tasks", len(issue_updates['closed']))
    for issue in issue_updates['closed']:
        _, task_info = tw.get_task(uuid=issue)
        log.info(
            "Completing task %s %s%s",
            issue,
            task_info.get('description', ''),
            notreally
        )
        if dry_run:
            continue

        if notify:
            send_notification(task_info, 'Completed', conf)

        try:
            tw.task_done(uuid=issue)
        except TaskwarriorError as e:
            log.exception("Unable to close task: %s" % e.stderr)

    # Send notifications
    if notify:
        only_on_new_tasks = _bool_option('notifications', 'only_on_new_tasks', False)
        if not only_on_new_tasks or len(issue_updates['new']) + len(issue_updates['changed']) + len(issue_updates['closed']) > 0:
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
    from bugwarrior.services import get_service

    keys = {}
    for target in targets:
        keys[target] = get_service(target).ISSUE_CLASS.UNIQUE_KEY
    return keys


def get_defined_udas_as_strings(conf, main_section):
    targets = [t.strip() for t in conf.get(main_section, 'targets').split(',')]
    services = set([conf.get(target, 'service') for target in targets])
    uda_list = build_uda_config_overrides(services)

    for uda in convert_override_args_to_taskrc_settings(uda_list):
        yield uda


def build_uda_config_overrides(targets):
    """ Returns a list of UDAs defined by given targets

    For all targets in `targets`, build a dictionary of configuration overrides
    representing the UDAs defined by the passed-in services (`targets`).

    Given a hypothetical situation in which you have two services, the first
    of which defining a UDA named 'serviceAid' ("Service A ID", string) and
    a second service defining two UDAs named 'serviceBproject'
    ("Service B Project", string) and 'serviceBnumber'
    ("Service B Number", numeric), this would return the following structure::

        {
            'uda': {
                'serviceAid': {
                    'label': 'Service A ID',
                    'type': 'string',
                },
                'serviceBproject': {
                    'label': 'Service B Project',
                    'type': 'string',
                },
                'serviceBnumber': {
                    'label': 'Service B Number',
                    'type': 'numeric',
                }
            }
        }

    """

    from bugwarrior.services import get_service

    targets_udas = {}
    for target in targets:
        targets_udas.update(get_service(target).ISSUE_CLASS.UDAS)
    return {
        'uda': targets_udas
    }


def convert_override_args_to_taskrc_settings(config, prefix=''):
    args = []
    for k, v in six.iteritems(config):
        if isinstance(v, dict):
            args.extend(
                convert_override_args_to_taskrc_settings(
                    v,
                    prefix='.'.join([
                        prefix,
                        k,
                    ]) if prefix else k
                )
            )
        else:
            v = six.text_type(v)
            left = (prefix + '.' if prefix else '') + k
            args.append('='.join([left, v]))
    return args
