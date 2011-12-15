import bitlyapi
import github2.client
import pprint
import taskw

gh = github2.client.Github()

gh_user = 'ralphbean'

from bugwarrior.util import rate_limit
from bugwarrior.config import load_config


@rate_limit
def _get_issues(tag):
    return [(tag, i) for i in gh.issues.list(tag)]

def pull():
    config = load_config()
    gh_user = config.get('github', 'github_user')
    bitly = bitlyapi.BitLy(
        config.get('bitly', 'api_user'),
        config.get('bitly', 'api_key'),
    )
    shorten = lambda url: bitly.shorten(longUrl=url)['url']

    has_issues = lambda repo: repo.has_issues
    repos = filter(has_issues, gh.repos.list(gh_user))
    issues = sum([_get_issues(gh_user + "/" + r.name) for r in repos], [])
    new_tasks = [{
        "description": "(bw) %s .. %s" % (
            issue.title[:35], shorten(issue.html_url)),
        "project": tag.split('/')[1],
    } for tag, issue in issues]

    known_tasks = taskw.load_tasks()
    known_tasks = known_tasks['pending'] + known_tasks['completed']
    known_descriptions = [t['description'] for t in known_tasks]
    for new_task in new_tasks:
        if not new_task['description'] in known_descriptions:
            pprint.pprint(new_task)
            taskw.task_add(**new_task)
