import bitlyapi
import pprint
import taskw

from bugwarrior.config import load_config
from bugwarrior.services import aggregate_issues


def pull():
    config = load_config()

    # Setup bitly shortening callback
    get_opt = lambda option: config.get('general', option)
    bitly = bitlyapi.BitLy(get_opt('bitly.api_user'), get_opt('bitly.api_key'))
    shorten = lambda url: bitly.shorten(longUrl=url)['url']

    # Get all the issues.  This can take a while.
    issues = aggregate_issues(config, shorten)

    # Check to see if they're already in the task db and add them if they're
    # not.
    # TODO refactor this code out into its own module
    known_tasks = taskw.load_tasks()
    known_tasks = known_tasks['pending'] + known_tasks['completed']
    known_descriptions = [t['description'] for t in known_tasks]
    for new_task in issues:
        if not new_task['description'] in known_descriptions:
            print "Adding task:", pprint.pformat(new_task)
            taskw.task_add(**new_task)
