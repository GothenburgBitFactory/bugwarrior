from twiggy import log

from bugwarrior.services import IssueService
from bugwarrior.config import die

import urllib2
import json


class BitbucketService(IssueService):
    base_api = 'https://api.bitbucket.org/1.0'
    base_url = 'http://bitbucket.org/'

    # A map of bitbucket priorities to taskwarrior priorities
    priorities = {
        'trivial': 'L',
        'minor': 'L',
        'major': 'M',
        'critical': 'H',
        'blocker': 'H',
    }

    def __init__(self, *args, **kw):
        super(BitbucketService, self).__init__(*args, **kw)

    @classmethod
    def validate_config(cls, config, target):
        if not config.has_option(target, 'username'):
            die("[%s] has no 'username'" % target)

        # TODO -- validate other options

        IssueService.validate_config(config, target)

    # Note -- not actually rate limited, I think.
    def pull(self, tag):
        url = self.base_api + '/repositories/%s/issues/' % tag
        f = urllib2.urlopen(url)
        response = json.loads(f.read())
        return [(tag, issue) for issue in response['issues']]

    def get_owner(self, issue):
        tag, issue = issue
        return issue.get('responsible', {}).get('username', None)

    def issues(self):
        user = self.config.get(self.target, 'username')

        url = self.base_api + '/users/' + user + '/'
        f = urllib2.urlopen(url)
        response = json.loads(f.read())
        repos = [repo.get('slug') for repo in response.get('repositories')]

        issues = sum([self.pull(user + "/" + repo) for repo in repos], [])
        log.debug(" Found {0} total.", len(issues))

        # Build a url for each issue
        for i in range(len(issues)):
            issues[i][1]['url'] = self.base_url + "/".join(
                issues[i][1]['resource_uri'].split('/')[3:]
            ).replace('issues', 'issue')

        issues = filter(self.include, issues)
        log.debug(" Pruned down to {0}", len(issues))

        return [{
            "description": self.description(
                issue['title'], issue['url'],
                issue['local_id'], cls="issue",
            ),
            "project": tag.split('/')[1],
            "priority": self.priorities.get(issue['priority'], 'M'),
        } for tag, issue in issues]
