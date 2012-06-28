from twiggy import log

from taskw import TaskWarrior


MARKUP = "(bw)"


def synchronize(issues):
    tw = TaskWarrior()

    # Load info about the task database
    tasks = tw.load_tasks()
    is_bugwarrior_task = lambda task: task.get('description', '').startswith(MARKUP)

    # Prune down to only tasks managed by bugwarrior
    for key in tasks.keys():
        tasks[key] = filter(is_bugwarrior_task, tasks[key])

    # Build a list of only the descriptions of those local bugwarrior tasks
    local_descs = [t['description'] for t in sum(tasks.values(), [])]

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

    log.struct(new=len(new_issues), completed=len(done_tasks))

    # Add new issues
    for issue in new_issues:
        log.info("Adding task {0}", issue['description'])
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
                log.info("Updating {0} on {1}",
                         key, upstream_issue['description'])
                task[key] = upstream_issue[key]
                id, task = tw.task_update(task)

    # Delete old issues
    for task in done_tasks:
        log.info("Completing task {0}", task['description'])
        tw.task_done(uuid=task['uuid'])
