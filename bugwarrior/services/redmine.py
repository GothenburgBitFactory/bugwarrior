import urllib
import urllib2
import json

import six
from twiggy import log

from bugwarrior.config import die
from bugwarrior.services import Issue, IssueService


class RedMineClient(object):
    def __init__(self, url, key):
        self.url = url
        self.key = key

    def find_issues(self, user_id=None):
        args = {}
        if user_id is not None:
            args["assigned_to_id"] = user_id
        return self.call_api("/issues.json", args)["issues"]

    def call_api(self, uri, get=None):
        url = self.url.rstrip("/") + uri

        if get:
            url += "?" + urllib.urlencode(get)

        req = urllib2.Request(url)
        req.add_header("X-Redmine-API-Key", self.key)

        res = urllib2.urlopen(req)

        return json.loads(res.read())


class RedMineIssue(Issue):
    URL = 'redmineurl'
    SUBJECT = 'redminesubject'
    ID = 'redmineid'

    UDAS = {
        URL: {
            'type': 'string',
            'label': 'Redmine URL',
        },
        SUBJECT: {
            'type': 'string',
            'label': 'Redmine Subject',
        },
        ID: {
            'type': 'string',
            'label': 'Redmine ID',
        },
    }
    UNIQUE_KEY = (URL, )

    PRIORITY_MAP = {
        'Low': 'L',
        'Normal': 'M',
        'High': 'H',
        'Urgent': 'H',
        'Immediate': 'H',
    }

    def to_taskwarrior(self):
        return {
            'project': self.get_project_name(),
            'priority': self.get_priority(),

            self.URL: self.get_issue_url(),
            self.SUBJECT: self.record['subject'],
            self.ID: self.record['id']
        }

    def get_priority(self):
        return self.PRIORITY_MAP.get(
            self.record.get('priority', {}).get('Name'),
            self.origin['default_priority']
        )

    def get_issue_url(self):
        return (
            self.origin['url'] + "/issues/" + six.text_type(self.record["id"])
        )

    def get_project_name(self):
        if self.origin['project_name']:
            return self.origin['project_name']
        return self.record["project"]["name"]

    def get_default_description(self):
        return self.build_default_description(
            title=self.record['subject'],
            url=self.get_processed_url(self.get_issue_url()),
            number=self.record['id'],
            cls='issue',
        )


class RedMineService(IssueService):
    ISSUE_CLASS = RedMineIssue
    CONFIG_PREFIX = 'redmine'

    def __init__(self, *args, **kw):
        super(RedMineService, self).__init__(*args, **kw)

        self.url = self.config_get('url').rstrip("/")
        self.key = self.config_get('key')
        self.user_id = self.config_get('user_id')

        self.client = RedMineClient(self.url, self.key)

        self.project_name = self.config_get_default('project_name')

    def get_service_metadata(self):
        return {
            'project_name': self.project_name,
            'url': self.url,
        }

    @classmethod
    def validate_config(cls, config, target):
        for k in ('redmine.url', 'redmine.key', 'redmine.user_id'):
            if not config.has_option(target, k):
                die("[%s] has no '%s'" % (target, k))

        IssueService.validate_config(config, target)

    def issues(self):
        issues = self.client.find_issues(self.user_id)
        log.name(self.target).debug(" Found {0} total.", len(issues))

        for issue in issues:
            yield self.get_issue_for_record(issue)
