from collections.abc import Iterable, Iterator
import copy
import json
import logging
import multiprocessing
import time
from typing import TYPE_CHECKING, Any, NamedTuple

from jinja2 import Template
from taskw.task import Task

from bugwarrior.config import get_service

if TYPE_CHECKING:
    from bugwarrior.config.validation import Config
    from bugwarrior.services import Issue, Service

log = logging.getLogger(__name__)

# Sentinels for process completion status
SERVICE_FINISHED_OK = 0
SERVICE_FINISHED_ERROR = 1


class CollectedIssue(NamedTuple):
    task_data: dict[str, Any]
    target: str
    identifier: str


class CollectionErrorData(NamedTuple):
    error_message: str
    target: str


def get_service_instances(conf: "Config") -> list["Service"]:
    return [
        get_service(service_config.service)(service_config, conf.main)
        for service_config in conf.service_configs
    ]


def _aggregate_issues(service: "Service", queue: multiprocessing.Queue) -> None:
    """This worker function is separated out from the main
    :func:`aggregate_issues` func only so that we can use multiprocessing
    on it for speed reasons.
    """

    start = time.time()
    target = service.config.target
    try:
        for issue in service.issues():
            queue.put(issue)
    except SystemExit as e:
        log.critical(f"Worker for [{target}] exited: {e}")
        queue.put((SERVICE_FINISHED_ERROR, target))
    except BaseException as e:
        if (request := getattr(e, 'request', None)) is not None:
            # Exceptions raised by requests library have the HTTP request
            # object stored as attribute. The request can have hooks attached
            # to it, and we need to remove them, as there can be unpickleable
            # methods. There is no one left to call these hooks anyway.
            request.hooks = {}
        log.exception(f"Worker for [{target}] failed")
        queue.put((SERVICE_FINISHED_ERROR, target))
    else:
        log.debug(f"Worker for [{target}] finished ok.")
        queue.put((SERVICE_FINISHED_OK, target))
    finally:
        duration = time.time() - start
        log.info(f"Done with [{target}] in {duration}.")


def aggregate_issues(
    conf: "Config", debug: bool
) -> Iterator[CollectedIssue | CollectionErrorData]:
    """Return all issues from every target."""
    log.info("Starting to aggregate remote issues.")

    queue = multiprocessing.Queue()

    services = get_service_instances(conf)

    log.info(f"Spawning {len(services)} workers.")

    if debug:
        for service in services:
            _aggregate_issues(service, queue)
    else:
        for service in services:
            proc = multiprocessing.Process(
                target=_aggregate_issues, args=(service, queue)
            )
            proc.start()

            # Sleep for 1 second here to try and avoid a race condition where
            # all N workers start up and ask the gpg-agent process for
            # information at the same time.  This causes gpg-agent to fumble
            # and tell some of our workers some incomplete things.
            time.sleep(1)

    currently_running = len(services)
    while currently_running > 0:
        issue = queue.get(True)
        try:
            yield TaskConstructor(issue).get_data_to_sync()
        except AttributeError:
            if isinstance(issue, tuple):
                currently_running -= 1
                completion_type, target = issue
                if completion_type == SERVICE_FINISHED_ERROR:
                    log.error(f"Aborted [{target}] due to critical error.")
                    yield CollectionErrorData('SERVICE FAILED', target)
                continue
            raise

    log.info("Done aggregating remote issues.")


def make_unique_identifier(
    unique_keys: Iterable[str], task_data: dict[str, Any]
) -> str:
    """For a given issue, make an identifier from its unique keys.

    This is not the same as the taskwarrior uuid, which is assigned
    only once the task is created.
    """
    subset = {key: task_data[key] for key in unique_keys}
    return json.dumps(subset, sort_keys=True)


class TaskConstructor:
    """Construct a taskwarrior task from a foreign record."""

    def __init__(self, issue: "Issue") -> None:
        self.issue = issue

    def get_added_tags(self) -> list[str]:
        added_tags = []
        for tag in self.issue.config.add_tags:
            tag = Template(tag).render(self.get_template_context())
            if tag:
                added_tags.append(tag)

        return added_tags

    def get_taskwarrior_record(self, refined: bool = True) -> dict[str, Any]:
        if not getattr(self, '_taskwarrior_record', None):
            self._taskwarrior_record = self.issue.to_taskwarrior()
        record = copy.deepcopy(self._taskwarrior_record)
        if refined:
            record = self.refine_record(record)
        if 'tags' not in record:
            record['tags'] = []
        if refined:
            record['tags'].extend(self.get_added_tags())

        # Blank priority should mean *no* priority
        if record['priority'] == '':
            record['priority'] = None
        return record

    def get_template_context(self) -> dict[str, Any]:
        context = self.get_taskwarrior_record(refined=False).copy()
        context.update(self.issue.extra)
        context.update({'description': self.issue.get_default_description()})
        return context

    def refine_record(self, record: dict[str, Any]) -> dict[str, Any]:
        for field in Task.FIELDS:
            if field in self.issue.config.templates:
                template = Template(self.issue.config.templates[field])
                record[field] = template.render(self.get_template_context())
            elif field == 'description':
                record['description'] = self.issue.get_default_description()
        return record

    def get_data_to_sync(self) -> CollectedIssue:
        task_data = self.get_taskwarrior_record()
        return CollectedIssue(
            task_data=task_data,
            identifier=make_unique_identifier(self.issue.UNIQUE_KEY, task_data),
            target=self.issue.config.target,
        )
