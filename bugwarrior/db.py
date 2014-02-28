import copy
import re

import six
from twiggy import log
from taskw import TaskWarriorShellout

from bugwarrior.config import asbool, NoOptionError
from bugwarrior.notifications import send_notification


MARKUP = "(bw)"


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
    for k in left:
        if k == 'annotations':
            left[k] = [v['description'] for v in left[k]]
            right[k] = [v['description'] for v in right[k]]
        if (
            isinstance(left[k], (list, tuple))
            and isinstance(right[k], (list, tuple))
        ):
            left[k] = set(left[k])
            right[k] = set(right[k])
        if left[k] != right[k]:
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


def find_local_uuid(tw, keys, issue, legacy_matching=True):
    if not issue['description']:
        raise ValueError('Issue %s has no description.' % issue)
    possibilities = set([])
    if legacy_matching:
        results = tw.filter_tasks({
            'description.startswith': issue.get_default_description()
        })
        possibilities = possibilities | set([
            task['uuid'] for task in results
        ])
    for key in keys:
        if key in issue:
            results = tw.filter_tasks({
                key: issue[key]
            })
            possibilities = possibilities | set([
                task['uuid'] for task in results
            ])
    if len(possibilities) == 1:
        return possibilities.pop()
    if len(possibilities) > 1:
        raise MultipleMatches(
            "Issue %s matched multiple IDs: %s" % (
                issue,
                possibilities
            )
        )
    raise NotFound(
        "No issue was found matching %s" % issue
    )


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
            'Service-defined UDAs (add these to your ~/.taskrc):'
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

    expected_task_ids = set([])
    for key in key_list.values():
        tasks = tw.filter_tasks({'%s.not' % key: ''})
        expected_task_ids = expected_task_ids | set([
            task['uuid'] for task in tasks
        ])
    legacy_matching = _bool_option('general', 'legacy_matching', 'True')
    if legacy_matching:
        starts_with_markup = tw.filter_tasks({
            'description.startswith': MARKUP,
        })
        expected_task_ids = expected_task_ids | set([
            task['uuid'] for task in starts_with_markup
        ])

    issue_updates = {
        'new': [],
        'existing': [],
        'changed': [],
        'closed': expected_task_ids,
    }
    for issue in issue_generator:
        try:
            existing_uuid = find_local_uuid(
                tw, key_list, issue, legacy_matching=legacy_matching
            )
            issue_dict = dict(issue)
            _, task = tw.get_task(uuid=existing_uuid)
            task_copy = copy.deepcopy(task)

            # Handle merging annotations
            for annotation in [
                a['description'] for a in task.get('annotations', [])
            ]:
                if not 'annotations' in issue_dict:
                    issue_dict['annotations'] = []
                found = False
                for new_annot in issue_dict['annotations']:
                    if get_annotation_hamming_distance(
                        new_annot, annotation
                    ) == 0:
                        found = True
                if not found:
                    issue_dict['annotations'].append(annotation)

            # Merging tags, too
            for tag in task.get('tags', []):
                if not 'tags' in issue_dict:
                    issue_dict['tags'] = []
                if tag not in issue_dict['tags']:
                    issue_dict['tags'].append(tag)

            task.update(issue_dict)
            if tasks_differ(task_copy, task):
                issue_updates['changed'].append(task)
            else:
                issue_updates['existing'].append(task)
            issue_updates['closed'].remove(existing_uuid)
        except MultipleMatches:
            log.name('bugwarrior').error(
                "Multiple matches found for issue: %s" % issue
            )
        except NotFound:
            issue_updates['new'].append(dict(issue))

    # Add new issues
    for issue in issue_updates['new']:
        log.name('db').info(
            "Adding task {0}",
            issue['description'].encode("utf-8")
        )
        if notify:
            send_notification(issue, 'Created', conf)
        tw.task_add(**issue)

    for issue in issue_updates['changed']:
        log.name('db').info(
            "Updating task {0}",
            issue['description'].encode("utf-8")
        )
        tw.task_update(issue)

    for issue in issue_updates['closed']:
        task_info = tw.get(uuid=issue)
        log.name('db').info(
            "Completing task {0}",
            task_info
        )
        if notify:
            send_notification(task_info, 'Completed', conf)
        tw.task_done(uuid=issue)

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
    from bugwarrior.services import SERVICES

    uda_output = []
    targets_udas = {}
    for target in targets:
        targets_udas.update(SERVICES[target].ISSUE_CLASS.UDAS)
    for name, uda_attributes in six.iteritems(targets_udas):
        for attrib, value in six.iteritems(uda_attributes):
            uda_output.append(
                (
                    'uda.%s.%s' % (name, attrib, ),
                    '%s' % (value, ),
                )
            )
    return sorted(uda_output)
