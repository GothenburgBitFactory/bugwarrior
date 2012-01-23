from twiggy import log

from taskw import TaskWarrior


MARKUP = "(bw)"


def synchronize(issues):
    tw = TaskWarrior()

    # Load info about the task database
    tasks = tw.load_tasks()
    is_bugwarrior_task = lambda task: task['description'].startswith(MARKUP)

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

    # Build the list of local tasks that need to be completed
    is_done = lambda task: task['description'] not in remote_descs
    done_tasks = filter(is_done, tasks['pending'])

    log.struct(new=len(new_issues), completed=len(done_tasks))

    for issue in new_issues:
        log.info("Adding task {0}", issue['description'])
        tw.task_add(**issue)

    for task in done_tasks:
        log.info("Completing task {0}", task['description'])
        tw.task_done(id=None, uuid=task['uuid'])
