import taskw
import pprint


def clean_issues(issues):
    """ Change "s into &dqout;s. """
    # TODO -- is it better to use http://wiki.python.org/moin/EscapingXml ?

    for i in range(len(issues)):
        for key in issues[i]:
            issues[i][key] = issues[i][key].replace('"', '&dquot;')

    return issues


def prune_issues(issues):
    known_tasks = taskw.load_tasks()
    known_tasks = known_tasks['pending'] + known_tasks['completed']
    known_descriptions = [t['description'] for t in known_tasks]
    novel = lambda issue: issue['description'] not in known_descriptions
    return filter(novel, issues)


def synchronize(issues):

    # TODO -- 'complete' issues that are closed upstream.

    # Escape any dangerous characters
    issues = clean_issues(issues)

    # Select only 'new' tasks
    issues = prune_issues(issues)

    for issue in issues:
        print "Adding task:", pprint.pformat(issue)
        taskw.task_add(**issue)
