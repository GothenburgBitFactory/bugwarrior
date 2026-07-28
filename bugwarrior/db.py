from collections.abc import Collection, Iterable, Iterator
import itertools
import logging
import re
import subprocess
from typing import TYPE_CHECKING, Any

from taskw import TaskWarriorShellout
from taskw.exceptions import TaskwarriorError

from bugwarrior.collect import CollectedIssue, CollectionErrorData
from bugwarrior.config import get_service
from bugwarrior.notifications import send_notification

if TYPE_CHECKING:
    from bugwarrior.config.schema import MainSectionConfig
    from bugwarrior.config.validation import Config

log = logging.getLogger(__name__)


class NotFound(Exception):
    pass


class MultipleMatches(Exception):
    pass


def get_managed_task_uuids(
    tw: TaskWarriorShellout, unique_key_sets: Iterable[Collection[str]]
) -> set[str]:
    expected_task_ids = set()
    for unique_keys in unique_key_sets:
        tasks = tw.filter_tasks(
            {
                'and': [(f'{key}.any', None) for key in unique_keys],
                'or': [('status', 'pending'), ('status', 'waiting')],
            }
        )
        expected_task_ids = expected_task_ids | {task['uuid'] for task in tasks}

    return expected_task_ids


def find_taskwarrior_uuid(
    tw: TaskWarriorShellout,
    unique_key_sets: Iterable[Collection[str]],
    issue: dict[str, Any],
) -> str:
    """For a given issue issue, find its local taskwarrior UUID.

    Assembles a list of task IDs existing in taskwarrior
    matching the supplied issue (`issue`) on the combination of any
    set of supplied unique identifiers (`keys`).

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

    :returns:
    * A single string UUID.

    :raises:
    * `bugwarrior.db.MultipleMatches`: if multiple matches were found.
    * `bugwarrior.db.NotFound`: if an issue was not found.

    """
    if not issue['description']:
        raise ValueError(f'Issue {issue} has no description.')

    possibilities = set()

    for unique_keys in unique_key_sets:
        if any(key in issue for key in unique_keys):
            results = tw.filter_tasks(
                {
                    'and': [(f"{key}.is", issue[key]) for key in unique_keys],
                    'or': [
                        ('status', 'pending'),
                        ('status', 'waiting'),
                        ('status', 'completed'),
                    ],
                }
            )
            new_possibilities = {task['uuid'] for task in results}
            # Previous versions of bugwarrior did not allow for reopening
            # completed tasks, so there could be multiple completed tasks
            # for the same issue if it was closed and reopened before that.
            if len(new_possibilities) > 1 and all(
                r['status'] == 'completed' for r in results
            ):
                for r in results[1:]:
                    for k in unique_keys:
                        if r[k] != results[0][k]:
                            break
                # All results are completed duplicates.
                new_possibilities = {new_possibilities.pop()}
            possibilities = possibilities | new_possibilities

    if len(possibilities) == 1:
        return possibilities.pop()

    if len(possibilities) > 1:
        raise MultipleMatches(
            "Issue {} matched multiple IDs: {}".format(
                issue['description'], possibilities
            )
        )

    raise NotFound(f"No issue was found matching {issue}")


def merge_annotations(local: dict[str, Any], remote: dict[str, Any]) -> list[str]:
    """
    Merge annotations. Order and duplication are preserved.
    """

    def normalize_annotation(annotation: str) -> str:
        return re.sub(r'[\W_]', '', str(annotation))

    local_annotations = local.get("annotations", [])
    normalized_local = set(map(normalize_annotation, local_annotations))
    new_annotations = [
        annotation
        for annotation in remote.get("annotations", [])
        if normalize_annotation(annotation) not in normalized_local
    ]
    return [*local_annotations, *new_annotations]


def merge_tags(
    main_conf: "MainSectionConfig", local: dict[str, Any], remote: dict[str, Any]
) -> list[str]:
    task_tags: set[str] = set(local.get("tags", []))
    if main_conf.replace_tags:
        task_tags &= set(main_conf.static_tags)

    return sorted(task_tags | set(remote.get("tags", [])))


def run_hooks(pre_import: list[str]) -> None:
    for hook in pre_import:
        exit_code = subprocess.call(hook, shell=True)
        if exit_code != 0:
            msg = f'Non-zero exit code {exit_code} on hook {hook}'
            log.error(msg)
            raise RuntimeError(msg)


def synchronize(
    issue_generator: Iterator[CollectedIssue | CollectionErrorData],
    conf: "Config",
    dry_run: bool = False,
) -> None:
    services = [service_config.service for service_config in conf.service_configs]
    unique_key_sets = build_unique_key_sets(services)
    uda_list = build_uda_config_overrides(services)

    if uda_list:
        log.info(
            'Service-defined UDAs exist: you can optionally use the '
            '`bugwarrior-uda` command to export a list of UDAs you can '
            'add to your taskrc file.'
        )

    # Before running CRUD operations, call the pre_import hook(s).
    run_hooks(conf.hooks.pre_import)

    notify = conf.notifications.notifications and not dry_run

    tw = TaskWarriorShellout(
        config_filename=conf.main.taskrc, config_overrides=uda_list, marshal=True
    )

    issue_updates = {'new': [], 'existing': [], 'changed': [], 'closed': []}

    issue_map = {}  # unique identifier -> issue
    successful_config_map = {
        service_config.target: service_config for service_config in conf.service_configs
    }

    for issue in issue_generator:
        if isinstance(issue, CollectionErrorData):
            successful_config_map.pop(issue.target)
            continue

        # De-duplicate issues coming in
        if issue.identifier in issue_map:
            log.debug(f"Merging tags and skipping. Seen {issue.identifier} of {issue}")
            # Merge and deduplicate tags.
            new_tags = sorted(
                set(issue_map[issue.identifier].task_data['tags'])
                | set(issue.task_data['tags'])
            )
            issue_map[issue.identifier].task_data['tags'] = new_tags

        else:
            issue_map[issue.identifier] = issue

    seen_uuids = set()
    for issue, target, _ in issue_map.values():
        # We received this issue from The Internet, but we're not sure what
        # kind of encoding the service providers may have handed us. Let's try
        # and decode all byte strings from UTF8 off the bat.  If we encounter
        # other encodings in the wild in the future, we can revise the handling
        # here. https://github.com/ralphbean/bugwarrior/issues/350
        for key in issue:
            if isinstance(issue[key], bytes):
                try:
                    issue[key] = issue[key].decode('utf-8')
                except UnicodeDecodeError:
                    log.warning(f"Failed to interpret {key!r} as utf-8")

        service_config = successful_config_map[target]

        try:
            existing_taskwarrior_uuid = find_taskwarrior_uuid(
                tw, unique_key_sets, issue
            )
        except MultipleMatches:
            log.exception("Multiple matches")
        except NotFound:  # Create new task
            issue_updates['new'].append(issue)
        else:  # Update existing task.
            seen_uuids.add(existing_taskwarrior_uuid)
            _, task = tw.get_task(uuid=existing_taskwarrior_uuid)

            if task['status'] == 'completed':
                # Reopen task
                task['status'] = 'pending'
                task['end'] = None

            # Drop static fields from the upstream issue.  We don't want to
            # overwrite local changes to fields we declare static.
            for field in itertools.chain(
                conf.main.static_fields, service_config.static_fields
            ):
                if field in issue:
                    del issue[field]

            # Merge annotations & tags from online into our task object
            if conf.main.merge_annotations:
                task["annotations"] = merge_annotations(task, issue)

            if conf.main.merge_tags:
                task["tags"] = merge_tags(conf.main, task, issue)

            issue.pop('annotations', None)
            issue.pop('tags', None)

            task.update(issue)

            if task.get_changes(keep=True):
                issue_updates['changed'].append(task)
            else:
                issue_updates['existing'].append(task)

    notreally = ' (not really)' if dry_run else ''
    # Add new issues
    log.info("Adding %i tasks", len(issue_updates['new']))
    for issue in issue_updates['new']:
        log.info("Adding task %s%s", issue['description'], notreally)

        if dry_run:
            continue
        if notify:
            send_notification(issue, 'Created', conf.notifications)

        try:
            new_task = tw.task_add(**issue)
            if issue.get('end'):
                tw.task_done(uuid=new_task['uuid'])
        except TaskwarriorError as e:
            log.exception(f"Unable to add task: {e.stderr}")
        else:
            seen_uuids.add(new_task['uuid'])

    log.info("Updating %i tasks", len(issue_updates['changed']))
    for issue in issue_updates['changed']:
        changes = '; '.join(
            [
                f'{field}: {ch[0]!r} -> {ch[1]!r}'
                for field, ch in issue.get_changes(keep=True).items()
            ]
        )
        log.info(
            "Updating task %s, %s; %s%s",
            str(issue['uuid']),
            issue['description'],
            changes,
            notreally,
        )
        if dry_run:
            continue

        try:
            _, updated_task = tw.task_update(issue)
            if issue.get('end'):
                tw.task_done(uuid=updated_task['uuid'])
        except TaskwarriorError as e:
            log.exception(f"Unable to modify task: {e.stderr}")

    log.debug(f'Closing tasks for succeeding services: {list(successful_config_map)}.')
    succeeded_service_task_uuids = get_managed_task_uuids(
        tw,
        build_unique_key_sets(
            service_config.service for service_config in successful_config_map.values()
        ),
    )
    issue_updates['closed'] = list(succeeded_service_task_uuids - seen_uuids)
    log.info("Closing %i tasks", len(issue_updates['closed']))
    for issue in issue_updates['closed']:
        _, task_info = tw.get_task(uuid=issue)
        log.info(
            "Completing task %s %s%s",
            issue,
            task_info.get('description', ''),
            notreally,
        )
        if dry_run:
            continue

        if notify:
            send_notification(task_info, 'Completed', conf.notifications)

        try:
            tw.task_done(uuid=issue)
        except TaskwarriorError as e:
            log.exception(f"Unable to close task: {e.stderr}")

    # Send notifications
    if notify:
        updates = (
            len(issue_updates['new'])
            + len(issue_updates['changed'])
            + len(issue_updates['closed'])
        )
        if not conf.notifications.only_on_new_tasks or updates > 0:
            send_notification(
                {
                    'description': (
                        f"New: {len(issue_updates['new'])}, "
                        f"Changed: {len(issue_updates['changed'])}, "
                        f"Completed: {len(issue_updates['closed'])}"
                    )
                },
                'bw_finished',
                conf.notifications,
            )


def build_unique_key_sets(services: Iterable[str]) -> set[tuple[str, ...]]:
    return {get_service(service).ISSUE_CLASS.UNIQUE_KEY for service in services}


def get_defined_udas_as_strings(conf: "Config") -> Iterator[str]:
    uda_list = build_uda_config_overrides(
        service_config.service for service_config in conf.service_configs
    )
    yield from convert_override_args_to_taskrc_settings(uda_list)


def build_uda_config_overrides(services: Iterable[str]) -> dict[str, Any]:
    """Returns a list of UDAs defined by given targets

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
    targets_udas = {}
    for service in services:
        targets_udas.update(get_service(service).ISSUE_CLASS.UDAS)
    return {'uda': targets_udas}


def convert_override_args_to_taskrc_settings(
    config: dict[str, Any], prefix: str = ''
) -> list[str]:
    args = []
    for k, v in config.items():
        if isinstance(v, dict):
            args.extend(
                convert_override_args_to_taskrc_settings(
                    v, prefix=f'{prefix}.{k}' if prefix else k
                )
            )
        else:
            v = str(v)
            left = (prefix + '.' if prefix else '') + k
            args.append(f'{left}={v}')
    return args
