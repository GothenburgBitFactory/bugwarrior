from twiggy import log
from taskw import TaskWarrior, TaskWarriorExperimental
from bugwarrior.notifications import send_notification
from bugwarrior.config import asbool, NoOptionError
import subprocess

MARKUP = "(bw)"


def synchronize(issues, conf):

    def _bool_option(section, option, default):
        try:
            return section in conf.sections() and \
                asbool(conf.get(section, option, default))
        except NoOptionError:
            return default

    notify = _bool_option('notifications', 'notifications', 'False')
    experimental = _bool_option('general', 'experimental', 'False')

    if experimental is True:
        # @TODO don't hardcode path to config filename.
        tw = TaskWarriorExperimental(config_filename='~/.bugwarrior_taskrc')
    else:
        tw = TaskWarrior()

    # Load info about the task database
    tasks = tw.load_tasks()

    is_bugwarrior_task = lambda task: \
        task.get('description', '').startswith(MARKUP)

    # Prune down to only tasks managed by bugwarrior
    for key in tasks.keys():
        tasks[key] = filter(is_bugwarrior_task, tasks[key])

    # Build a list of only the descriptions of those local bugwarrior tasks
    local_descs = [t['description'] for t in sum(tasks.values(), [])
                   if t['status'] not in ('deleted')]

    # Now for the remote data.
    # Build a list of only the descriptions of those remote issues
    remote_descs = [i['description'] for i in issues]

    # Build the list of tasks that need to be added
    is_new = lambda issue: issue['description'] not in local_descs
    new_issues = filter(is_new, issues)
    old_issues = filter(lambda i: not is_new(i), issues)

    # Build the list of local tasks that need to be completed
    is_done = lambda task: task['description'] not in remote_descs
    done_tasks = filter(is_done, tasks['pending'])

    log.name('db').struct(new=len(new_issues), completed=len(done_tasks))

    # Add new issues
    for issue in new_issues:
        log.name('db').info(
            "Adding task {0}",
            issue['description'].encode("utf-8")
        )
        if notify:
            send_notification(issue, 'Created', conf)
        tw.task_add(**issue)

    # Update any issues that may have had new properties added.  These are
    # usually annotations that come from comments in the issue thread.
    pending_descriptions = [t['description'] for t in tasks['pending']]
    for upstream_issue in old_issues:
        if upstream_issue['description'] not in pending_descriptions:
            continue

        id, task = tw.get_task(description=upstream_issue['description'])
        for key in upstream_issue:
            if key not in task:
                if experimental is True and "annotation_" in key:
                    # TaskWarrior doesn't currently (2.2.0) allow for setting
                    # the annotation entry key. This means that each annotation
                    # key will always be updated to the current date and time,
                    # which in turn means BW will always think a task has been
                    # updated. Until this is resolved in 2.3.0, ignore
                    # annotation updates in experimental mode.
                    continue
                log.name('db').info(
                    "Updating {0} on {1}",
                    key,
                    upstream_issue['description'].encode("utf-8"),
                )
                if notify:
                    send_notification(upstream_issue, 'Updated', conf)
                task[key] = upstream_issue[key]
                id, task = tw.task_update(task)

    # Delete old issues
    for task in done_tasks:
        log.name('db').info(
            "Completing task {0}",
            task['description'].encode("utf-8"),
        )
        if notify:
            send_notification(task, 'Completed', conf)

        tw.task_done(uuid=task['uuid'])
        if experimental is True:
            # `task merge` only updates/adds tasks, it won't delete them, so
            # call task_done() on the primary TW task database.
            tw_done = TaskWarriorExperimental()
            tw_done.task_done(uuid=task['uuid'])

    # Merge tasks with users local DB
    if experimental is True:
        # Call task merge from users local database
        config = tw.load_config(config_filename='~/.bugwarrior_taskrc')
        bwtask_data = "%s/" % config['data']['location']
        subprocess.call([
            'task', 'rc.verbose=nothing', 'rc.merge.autopush=no',
            'merge', bwtask_data])
        # Delete completed tasks from Bugwarrior tasks DB. This allows for
        # assigning/unassigning tasks in a remote service, and tracking status
        # changes in Bugwarrior.
        subprocess.call([
            'task', 'rc:~/.bugwarrior_taskrc', 'rc.verbose=nothing',
            'rc.confirmation=no', 'rc.bulk=100', 'status:completed',
            'delete'])

    # Send notifications
    if notify:
        send_notification(
            dict(description="New: %d, Completed: %d" % (
                len(new_issues), len(done_tasks)
            )),
            'bw_finished',
            conf,
        )
