import copy
import logging
import multiprocessing
import time

from jinja2 import Template
from pkg_resources import iter_entry_points

from taskw.task import Task

log = logging.getLogger(__name__)

# Sentinels for process completion status
SERVICE_FINISHED_OK = 0
SERVICE_FINISHED_ERROR = 1


def get_service(service_name):
    epoint = iter_entry_points(group='bugwarrior.service', name=service_name)
    try:
        epoint = next(epoint)
    except StopIteration:
        return None

    return epoint.load()


def _aggregate_issues(conf, main_section, target, queue):
    """ This worker function is separated out from the main
    :func:`aggregate_issues` func only so that we can use multiprocessing
    on it for speed reasons.
    """

    start = time.time()

    try:
        service = get_service(conf[target].service)(
            conf[target], conf[main_section])
        issue_count = 0
        for issue in service.issues():
            queue.put(issue)
            issue_count += 1
    except SystemExit as e:
        log.critical(f"Worker for [{target}] exited: {e}")
        queue.put((SERVICE_FINISHED_ERROR, target))
    except BaseException as e:
        if hasattr(e, 'request') and e.request:
            # Exceptions raised by requests library have the HTTP request
            # object stored as attribute. The request can have hooks attached
            # to it, and we need to remove them, as there can be unpickleable
            # methods. There is no one left to call these hooks anyway.
            e.request.hooks = {}
        log.exception(f"Worker for [{target}] failed: {e}")
        queue.put((SERVICE_FINISHED_ERROR, target))
    else:
        log.debug(f"Worker for [{target}] finished ok.")
        queue.put((SERVICE_FINISHED_OK, target))
    finally:
        duration = time.time() - start
        log.info(f"Done with [{target}] in {duration}.")


def aggregate_issues(conf, main_section, debug):
    """ Return all issues from every target. """
    log.info("Starting to aggregate remote issues.")

    # Create and call service objects for every target in the config
    targets = conf[main_section].targets

    queue = multiprocessing.Queue()

    log.info("Spawning %i workers." % len(targets))

    if debug:
        for target in targets:
            _aggregate_issues(conf, main_section, target, queue)
    else:
        for target in targets:
            proc = multiprocessing.Process(
                target=_aggregate_issues,
                args=(conf, main_section, target, queue)
            )
            proc.start()

            # Sleep for 1 second here to try and avoid a race condition where
            # all N workers start up and ask the gpg-agent process for
            # information at the same time.  This causes gpg-agent to fumble
            # and tell some of our workers some incomplete things.
            time.sleep(1)

    currently_running = len(targets)
    while currently_running > 0:
        issue = queue.get(True)
        try:
            yield TaskConstructor(issue).get_taskwarrior_record()
        except AttributeError:
            if isinstance(issue, tuple):
                currently_running -= 1
                completion_type, target = issue
                if completion_type == SERVICE_FINISHED_ERROR:
                    log.error(f"Aborted [{target}] due to critical error.")
                    yield ('SERVICE FAILED', target)
                continue
            yield issue

    log.info("Done aggregating remote issues.")


class TaskConstructor:
    """ Construct a taskwarrior task from a foreign record. """

    def __init__(self, issue):
        self.issue = issue

    def get_added_tags(self):
        added_tags = []
        for tag in self.issue.config.add_tags:
            tag = Template(tag).render(self.get_template_context())
            if tag:
                added_tags.append(tag)

        return added_tags

    def get_taskwarrior_record(self, refined=True) -> dict:
        if not getattr(self, '_taskwarrior_record', None):
            self._taskwarrior_record = self.issue.to_taskwarrior()
        record = copy.deepcopy(self._taskwarrior_record)
        if refined:
            record = self.refine_record(record)
        if 'tags' not in record:
            record['tags'] = []
        if refined:
            record['tags'].extend(self.get_added_tags())
        return record

    def get_template_context(self):
        context = (
            self.get_taskwarrior_record(refined=False).copy()
        )
        context.update(self.issue.extra)
        context.update({
            'description': self.issue.get_default_description(),
        })
        return context

    def refine_record(self, record):
        for field in Task.FIELDS.keys():
            if field in self.issue.config.templates:
                template = Template(self.issue.config.templates[field])
                record[field] = template.render(self.get_template_context())
            elif field == 'description':
                record['description'] = self.issue.get_default_description()
        return record
