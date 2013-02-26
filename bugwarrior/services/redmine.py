from twiggy import log

from bugwarrior.services import IssueService
from bugwarrior.config import die

import datetime
import urllib
import urllib2
import json


class Client(object):
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


class RedMineService(IssueService):
    def __init__(self, *args, **kw):
        super(RedMineService, self).__init__(*args, **kw)

        self.url = self.config.get(self.target, 'url').rstrip("/")
        self.key = self.config.get(self.target, 'key')
        self.user_id = self.config.get(self.target, 'user_id')

        self.client = Client(self.url, self.key)

        self.project_name = None
        if self.config.has_option(self.target, "project_name"):
            self.project_name = self.config.get(self.target, "project_name")

    @classmethod
    def validate_config(cls, config, target):
        for k in ('url', 'key', 'user_id'):
            if not config.has_option(target, k):
                die("[%s] has no '%s'" % (target, k))

        IssueService.validate_config(config, target)

    def get_issue_url(self, issue):
        return self.url + "/issues/" + str(issue["id"])

    def get_project_name(self, issue):
        if self.project_name:
            return self.project_name
        return issue["project"]["name"]

    def issues(self):
        issues = self.client.find_issues(self.user_id)
        log.name(self.target).debug(" Found {0} total.", len(issues))

        return [dict(
            description=self.description(
                issue["subject"],
                self.get_issue_url(issue),
                issue["id"], cls="issue"),
            project=self.get_project_name(issue),
            priority=self.default_priority,
        ) for issue in issues]
