import six
import requests
import typing_extensions

from bugwarrior import config
from bugwarrior.services import Issue, IssueService, ServiceClient

import logging
log = logging.getLogger(__name__)


class TeamLabConfig(config.ServiceConfig, prefix='teamlab'):
    service: typing_extensions.Literal['teamlab']
    hostname: str
    login: str
    password: str

    project_name: str = ''


class TeamLabClient(ServiceClient):
    def __init__(self, hostname, verbose=False):
        self.hostname = hostname
        self.verbose = verbose
        self.token = None

    def authenticate(self, login, password):
        resp = self.call_api("/api/1.0/authentication.json", post={
            "userName": six.text_type(login),
            "password": six.text_type(password),
        })

        self.token = six.text_type(resp["token"])

    def get_task_list(self):
        resp = self.call_api("/api/1.0/project/task/@self.json")
        return resp

    def call_api(self, uri, post=None, params=None):
        uri = "http://" + self.hostname + uri
        kwargs = {'params': params}

        if self.token:
            kwargs['headers'] = {'Authorization': self.token}

        response = (requests.post(uri, data=post, **kwargs) if post
                    else requests.get(uri, **kwargs))

        return self.json_response(response)


class TeamLabIssue(Issue):
    URL = 'teamlaburl'
    FOREIGN_ID = 'teamlabid'
    TITLE = 'teamlabtitle'
    PROJECTOWNER_ID = 'teamlabprojectownerid'

    UDAS = {
        URL: {
            'type': 'string',
            'label': 'Teamlab URL',
        },
        FOREIGN_ID: {
            'type': 'string',
            'label': 'Teamlab ID',
        },
        TITLE: {
            'type': 'string',
            'label': 'Teamlab Title',
        },
        PROJECTOWNER_ID: {
            'type': 'string',
            'label': 'Teamlab ProjectOwner ID',
        }
    }
    UNIQUE_KEY = (URL, )

    def to_taskwarrior(self):
        return {
            'project': self.get_project(),
            'priority': self.get_priority(),

            self.TITLE: self.record['title'],
            self.FOREIGN_ID: self.record['id'],
            self.URL: self.get_issue_url(),
            self.PROJECTOWNER_ID: self.record['projectOwner']['id'],
        }

    def get_default_description(self):
        return self.build_default_description(
            title=self.record['title'],
            url=self.get_processed_url(self.get_issue_url()),
            number=self.record['id'],
            cls='issue',
        )

    def get_project(self):
        return self.origin['project_name']

    def get_issue_url(self):
        return "http://%s/products/projects/tasks.aspx?prjID=%d&id=%d" % (
            self.origin['hostname'],
            self.record["projectOwner"]["id"],
            self.record["id"]
        )

    def get_priority(self):
        if self.record.get("priority") == 1:
            return "H"
        return self.origin['default_priority']


class TeamLabService(IssueService):
    ISSUE_CLASS = TeamLabIssue
    CONFIG_SCHEMA = TeamLabConfig

    def __init__(self, *args, **kw):
        super(TeamLabService, self).__init__(*args, **kw)

        _password = self.get_password('password', self.config.login)

        self.client = TeamLabClient(self.config.hostname)
        self.client.authenticate(self.config.login, _password)

        self.project_name = self.config.project_name or self.config.hostname

    @staticmethod
    def get_keyring_service(config):
        return f"teamlab://{config.login}@{config.hostname}"

    def get_service_metadata(self):
        return {
            'hostname': self.config.hostname,
            'project_name': self.project_name,
        }

    def get_owner(self, issue):
        # TODO
        raise NotImplementedError(
            "This service has not implemented support for 'only_if_assigned'.")

    def issues(self):
        issues = self.client.get_task_list()
        log.debug(" Remote has %i total issues.", len(issues))

        # Filter out closed tasks.
        issues = [i for i in issues if i["status"] == 1]
        log.debug(" Remote has %i active issues.", len(issues))

        for issue in issues:
            yield self.get_issue_for_record(issue)
