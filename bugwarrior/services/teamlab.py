from twiggy import log

from bugwarrior.services import IssueService
from bugwarrior.config import die, get_service_password

import datetime
import json
import urllib
import urllib2


class Client(object):
    def __init__(self, hostname, verbose=False):
        self.hostname = hostname
        self.verbose = verbose
        self.token = None

    def authenticate(self, login, password):
        resp = self.call_api("/api/1.0/authentication.json", post={
            "userName": str(login),
            "password": str(password),
        })

        self.token = str(resp["token"])

    def get_task_list(self):
        resp = self.call_api("/api/1.0/project/task/@self.json")
        return resp

    def call_api(self, uri, post=None, get=None):
        uri = "http://" + self.hostname + uri

        if post is None:
            data = None
        else:
            data = urllib.urlencode(post)

        if get is not None:
            uri += "?" + urllib.urlencode(get)

        self.log("Fetching %s" % uri)

        req = urllib2.Request(uri, data)
        if self.token is not None:
            req.add_header("Authorization", self.token)
        req.add_header("Accept", "application/json")

        res = urllib2.urlopen(req)
        if res.getcode() >= 400:
            raise Exception("Error accessing the API: %s" % res.read())

        response = res.read()

        return json.loads(response)["response"]

    def log(self, message):
        if self.verbose:
            print message


class TeamLabService(IssueService):
    def __init__(self, *args, **kw):
        super(TeamLabService, self).__init__(*args, **kw)

        self.hostname = self.config.get(self.target, 'hostname')
        _login = self.config.get(self.target, 'login')
        _password = self.config.get(self.target, 'password')
        if not _password or _password.startswith("@oracle:"):
            service = "teamlab://%s@%s" % (_login, self.hostname)
            _password = get_service_password(service, _login, oracle=_password,
                                            interactive=self.config.interactive)

        self.client = Client(self.hostname)
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

    def get_issue_url(self, issue):
        return "http://%s/products/projects/tasks.aspx?prjID=%d&id=%d" \
            % (self.hostname, issue["projectOwner"]["id"], issue["id"])

    def get_priority(self, issue):
        if issue["priority"] == 1:
            return "H"
        else:
            return "M"

    def issues(self):
        issues = self.client.get_task_list()
        log.name(self.target).debug(
            " Remote has {0} total issues.", len(issues))
        if not issues:
            return []

        # Filter out closed tasks.
        issues = filter(lambda i: i["status"] == 1, issues)
        log.name(self.target).debug(
            " Remote has {0} active issues.", len(issues))

        return [dict(
            description=self.description(
                issue["title"],
                self.get_issue_url(issue),
                issue["id"], cls="issue"),
            project=self.project_name,
            priority=self.get_priority(issue),
        ) for issue in issues]
