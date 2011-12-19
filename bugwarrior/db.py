import taskw
import pprint


MARKUP = "(bw)"


def clean_issues(issues):
    """ Change "s into &dqout;s. """
    # TODO -- is it better to use http://wiki.python.org/moin/EscapingXml ?
    # TODO -- should this be moved into http://github.com/ralphbean/taskw ?

    replacements = {
        '"': '&dquot;',
        '[': '&open;',
        ']': '&close;',
    }

    for i in range(len(issues)):
        for key in issues[i]:
            for unsafe, safe in replacements.iteritems():
                issues[i][key] = issues[i][key].replace(unsafe, safe)

    return issues



def synchronize(issues):
    # Load info about the task database
    tasks = taskw.load_tasks()
    is_bugwarrior_task = lambda task: task['description'].startswith(MARKUP)

    # Prune down to only tasks managed by bugwarrior
    for key in tasks.keys():
        tasks[key] = filter(is_bugwarrior_task, tasks[key])

    # Build a list of only the descriptions of those local bugwarrior tasks
    local_descs = [t['description'] for t in sum(tasks.values(), [])]


    # Now the remote data.
    # Escape any dangerous characters.
    issues = clean_issues(issues)

    # Build a list of only the descriptions of those remote issues
    remote_descs = [i['description'] for i in issues]

    # Build the list of tasks that need to be added
    is_new = lambda issue: issue['description'] not in local_descs
    new_issues = filter(is_new, issues)

    # Build the list of local tasks that need to be completed
    is_done = lambda task: task['description'] not in remote_descs
    done_tasks = filter(is_done, tasks['pending'])

    for issue in new_issues:
        print "Adding task:", pprint.pformat(issue)
        taskw.task_add(**issue)

    for task in done_tasks:
        print "Completed task:", pprint.pformat(task)
        taskw.task_done(id=None, uuid=task['uuid'])
