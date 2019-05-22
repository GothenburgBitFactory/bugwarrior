import six
import requests
import re

from bugwarrior.config import die, asbool
from bugwarrior.services import Issue, IssueService, ServiceClient
from taskw import TaskWarriorShellout

import logging
log = logging.getLogger(__name__)


class RedMineClient(ServiceClient):
    def __init__(self, url, key, auth, issue_limit, verify_ssl):
        self.url = url
        self.key = key
        self.auth = auth
        self.issue_limit = issue_limit
        self.verify_ssl = verify_ssl

    def find_issues(self, issue_limit=100, only_if_assigned=False):
        args = {}
        # TODO: if issue_limit is greater than 100, implement pagination to return all issues.
        # Leave the implementation of this to the unlucky soul with >100 issues assigned to them.
        if issue_limit is not None:
            args["limit"] = issue_limit

        if only_if_assigned:
            args["assigned_to_id"] = 'me'
        return self.call_api("/issues.json", args)["issues"]

    def call_api(self, uri, params):
        url = self.url.rstrip("/") + uri
        kwargs = {
            'headers': {'X-Redmine-API-Key': self.key},
            'params': params}

        if self.auth:
            kwargs['auth'] = self.auth

        kwargs['verify'] = self.verify_ssl

        return self.json_response(requests.get(url, **kwargs))


class RedMineIssue(Issue):
    URL = 'redmineurl'
    SUBJECT = 'redminesubject'
    ID = 'redmineid'
    DESCRIPTION = 'redminedescription'
    TRACKER = 'redminetracker'
    STATUS = 'redminestatus'
    AUTHOR = 'redmineauthor'
    CATEGORY = 'redminecategory'
    START_DATE = 'redminestartdate'
    SPENT_HOURS = 'redminespenthours'
    ESTIMATED_HOURS = 'redmineestimatedhours'
    CREATED_ON = 'redminecreatedon'
    UPDATED_ON = 'redmineupdatedon'
    DUEDATE = 'redmineduedate'
    ASSIGNED_TO = 'redmineassignedto'

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
            'type': 'numeric',
            'label': 'Redmine ID',
        },
        DESCRIPTION: {
            'type': 'string',
            'label': 'Redmine Description',
        },
        TRACKER: {
            'type': 'string',
            'label': 'Redmine Tracker',
        },
        STATUS: {
            'type': 'string',
            'label': 'Redmine Status',
        },
        AUTHOR: {
            'type': 'string',
            'label': 'Redmine Author',
        },
        CATEGORY: {
            'type': 'string',
            'label': 'Redmine Category',
        },
        START_DATE: {
            'type': 'date',
            'label': 'Redmine Start Date',
        },
        SPENT_HOURS: {
            'type': 'duration',
            'label': 'Redmine Spent Hours',
        },
        ESTIMATED_HOURS: {
            'type': 'duration',
            'label': 'Redmine Estimated Hours',
        },
        CREATED_ON: {
            'type': 'date',
            'label': 'Redmine Created On',
        },
        UPDATED_ON: {
            'type': 'date',
            'label': 'Redmine Updated On',
        },
        DUEDATE: {
            'type': 'date',
            'label': 'Redmine Due Date'
        },
        ASSIGNED_TO: {
            'type': 'string',
            'label': 'Redmine Assigned To',
        },

    }
    UNIQUE_KEY = (ID, )

    PRIORITY_MAP = {
        'Low': 'L',
        'Normal': 'M',
        'High': 'H',
        'Urgent': 'H',
        'Immediate': 'H',
    }

    def to_taskwarrior(self):
        due_date = self.record.get('due_date')
        start_date = self.record.get('start_date')
        updated_on = self.record.get('updated_on')
        created_on = self.record.get('created_on')
        spent_hours = self.record.get('spent_hours')
        estimated_hours = self.record.get('estimated_hours')
        category = self.record.get('category')
        assigned_to = self.record.get('assigned_to')

        if due_date:
            due_date = self.parse_date(due_date).replace(microsecond=0)
        if start_date:
            start_date = self.parse_date(start_date).replace(microsecond=0)
        if updated_on:
            updated_on = self.parse_date(updated_on).replace(microsecond=0)
        if created_on:
            created_on = self.parse_date(created_on).replace(microsecond=0)
        if spent_hours:
            spent_hours = str(spent_hours) + ' hours'
            spent_hours = self.get_converted_hours(spent_hours)
        if estimated_hours:
            estimated_hours = str(estimated_hours) + ' hours'
            estimated_hours = self.get_converted_hours(estimated_hours)
        if category:
            category = category['name']
        if assigned_to:
            assigned_to = assigned_to['name']

        return {
            'project': self.get_project_name(),
            'annotations': self.extra.get('annotations', []),
            'priority': self.get_priority(),
            self.URL: self.get_issue_url(),
            self.SUBJECT: self.record['subject'],
            self.ID: self.record['id'],
            self.DESCRIPTION: self.record.get('description', ''),
            self.TRACKER: self.record['tracker']['name'],
            self.STATUS: self.record['status']['name'],
            self.AUTHOR: self.record['author']['name'],
            self.ASSIGNED_TO: assigned_to,
            self.CATEGORY: category,
            self.START_DATE: start_date,
            self.CREATED_ON: created_on,
            self.UPDATED_ON: updated_on,
            self.DUEDATE: due_date,
            self.ESTIMATED_HOURS: estimated_hours,
            self.SPENT_HOURS: spent_hours,
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

    def get_converted_hours(self, estimated_hours):
        tw = TaskWarriorShellout()
        calc = tw._execute('calc', estimated_hours)
        return (
            calc[0].rstrip()
        )

    def get_project_name(self):
        if self.origin['project_name']:
            return self.origin['project_name']
        # TODO: It would be nice to use the project slug (if the Redmine
        # instance supports it), but this would require (1) an API call
        # to get the list of projects, and then a look up between the
        # project ID contained in self.record and the list of projects.
        return re.sub(r'[^a-zA-Z0-9]', '', self.record["project"]["name"]).lower()

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

        self.url = self.config.get('url').rstrip("/")
        self.key = self.get_password('key')
        self.issue_limit = self.config.get('issue_limit')

        self.verify_ssl = self.config.get(
            'verify_ssl', default=True, to_type=asbool
        )

        login = self.config.get('login')
        if login:
            password = self.get_password('password', login)
        auth = (login, password) if (login and password) else None
        self.client = RedMineClient(self.url, self.key, auth, self.issue_limit, self.verify_ssl)

        self.project_name = self.config.get('project_name')

    def get_service_metadata(self):
        return {
            'project_name': self.project_name,
            'url': self.url,
        }

    @staticmethod
    def get_keyring_service(service_config):
        url = service_config.get('url')
        login = service_config.get('login')
        return "redmine://%s@%s/" % (login, url)

    @classmethod
    def validate_config(cls, service_config, target):
        for k in ('url', 'key'):
            if k not in service_config:
                die("[%s] has no 'redmine.%s'" % (target, k))

        IssueService.validate_config(service_config, target)

    def issues(self):
        only_if_assigned = self.config.get('only_if_assigned', False)
        issues = self.client.find_issues(self.issue_limit, only_if_assigned)
        log.debug(" Found %i total.", len(issues))
        for issue in issues:
            yield self.get_issue_for_record(issue)
