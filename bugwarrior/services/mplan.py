from twiggy import log

from bugwarrior.services import IssueService
from bugwarrior.config import die, get_service_password

import datetime
import urllib2
import json

import megaplan


class MegaplanService(IssueService):
    def __init__(self, *args, **kw):
        super(MegaplanService, self).__init__(*args, **kw)

        self.hostname = self.config.get(self.target, 'hostname')
        _login = self.config.get(self.target, 'login')
        _password = self.config.get(self.target, 'password')
        if not _password or _password.startswith("@oracle:"):
            service = "megaplan://%s@%s" % (_login, self.hostname)
            _password = get_service_password(service, _login, oracle=_password,
                                            interactive=self.config.interactive)

        self.client = megaplan.Client(self.hostname)
        self.client.authenticate(_login, _password)

        self.project_name = self.hostname
        if self.config.has_option(self.target, "project_name"):
            self.project_name = self.config.get(self.target, "project_name")

    @classmethod
    def validate_config(cls, config, target):
        for k in ('login', 'password', 'hostname'):
            if not config.has_option(target, k):
                die("[%s] has no '%s'" % (target, k))

        IssueService.validate_config(config, target)

    def get_issue_id(self, issue):
        if issue["Id"] > 1000000:
            return issue["Id"] - 1000000
        return issue["Id"]

    def get_issue_title(self, issue):
        parts = issue["Name"].split("|")
        return parts[-1].strip()

    def get_issue_url(self, issue):
        return "https://%s/task/%d/card/" % (self.hostname, issue["Id"])

    def issues(self):
        issues = self.client.get_actual_tasks()
        log.name(self.target).debug(" Found {0} total.", len(issues))

        return [dict(
            description=self.description(
                self.get_issue_title(issue),
                self.get_issue_url(issue),
                self.get_issue_id(issue),
                cls="issue"),
            project=self.project_name,
            priority=self.default_priority,
        ) for issue in issues]
