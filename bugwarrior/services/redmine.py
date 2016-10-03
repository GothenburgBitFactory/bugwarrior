import six
import requests

from bugwarrior.config import die
from bugwarrior.services import Issue, IssueService, ServiceClient

import logging
log = logging.getLogger(__name__)


class RedMineClient(ServiceClient):
    def __init__(self, url, key, auth, issue_limit):
        self.url = url
        self.key = key
        self.auth = auth
        self.issue_limit = issue_limit

    def find_issues(self, user_id=None, issue_limit=25):
        args = {}
        if user_id is not None:
            args["assigned_to_id"] = user_id
        if issue_limit is not None:
            args["limit"] = issue_limit
        return self.call_api("/issues.json", args)["issues"]

    def call_api(self, uri, params):
        url = self.url.rstrip("/") + uri
        kwargs = {
            'headers': {'X-Redmine-API-Key': self.key},
            'params': params}

        if self.auth:
            kwargs['auth'] = self.auth

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
        duedate = self.record.get('due_date')
        if duedate:
            duedate = self.parse_date(duedate)
        spent_hours = self.record.get('spent_hours')
        if spent_hours:
            spent_hours = str(spent_hours) + ' hours'
        estimated_hours = self.record.get('estimated_hours')
        if estimated_hours:
            estimated_hours = str(estimated_hours) + ' hours'
        category = self.record.get('category')
        if category:
            category = category['name']

        return {
            'project': self.get_project_name(),
            'due': duedate,
            'annotations': self.extra.get('annotations', []),
            'priority': self.get_priority(),

            self.URL: self.get_issue_url(),
            self.SUBJECT: self.record['subject'],
            self.ID: self.record['id'],
            self.DESCRIPTION: self.record['description'],
            self.TRACKER: self.record['tracker']['name'],
            self.STATUS: self.record['status']['name'],
            self.AUTHOR: self.record['author']['name'],
            self.CATEGORY: category,
            self.START_DATE: self.record['start_date'],
            self.CREATED_ON: self.record['created_on'],
            self.UPDATED_ON: self.record['updated_on'],
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
        self.issue_limit = self.config_get('issue_limit')

        login = self.config_get_default('login')
        if login:
            password = self.config_get_password('password', login)
        auth = (login, password) if (login and password) else None
        self.client = RedMineClient(self.url, self.key, auth, self.issue_limit)

        self.project_name = self.config_get_default('project_name')

    def get_service_metadata(self):
        return {
            'project_name': self.project_name,
            'url': self.url,
        }

    @classmethod
    def get_keyring_service(cls, config, section):
        url = config.get(section, cls._get_key('url'))
        login = config.get(section, cls._get_key('login'))
        user_id = config.get(section, cls._get_key('user_id'))
        return "redmine://%s@%s/%s" % (login, url, user_id)

    @classmethod
    def validate_config(cls, config, target):
        for k in ('redmine.url', 'redmine.key', 'redmine.user_id'):
            if not config.has_option(target, k):
                die("[%s] has no '%s'" % (target, k))

        IssueService.validate_config(config, target)

    def issues(self):
        issues = self.client.find_issues(self.user_id, self.issue_limit)
        log.debug(" Found %i total.", len(issues))

        for issue in issues:
            yield self.get_issue_for_record(issue)
