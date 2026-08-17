from collections.abc import Iterator
import logging
import multiprocessing
import time
from typing import TYPE_CHECKING, NamedTuple

from bugwarrior.config import get_service

if TYPE_CHECKING:
    from bugwarrior.config.validation import Config
    from bugwarrior.services import Service
    from bugwarrior.task import Task

log = logging.getLogger(__name__)

# Sentinels for process completion status
SERVICE_FINISHED_OK = 0
SERVICE_FINISHED_ERROR = 1


class CollectedIssue(NamedTuple):
    task: "Task"
    target: str


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
        for task in service.issues():
            queue.put(CollectedIssue(task=task, target=target))
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
        log.exception(f"Worker for [{target}] failed: {e}")
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

    log.info("Spawning %i workers." % len(services))

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
        item = queue.get(True)
        if isinstance(item, CollectedIssue):
            yield item
        else:
            currently_running -= 1
            completion_type, target = item
            if completion_type == SERVICE_FINISHED_ERROR:
                log.error(f"Aborted [{target}] due to critical error.")
                yield CollectionErrorData('SERVICE FAILED', target)

    log.info("Done aggregating remote issues.")
