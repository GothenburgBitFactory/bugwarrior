from __future__ import absolute_import
from builtins import str


import six
from jinja2 import Template
from jira.client import JIRA as BaseJIRA
from requests.cookies import RequestsCookieJar
from dateutil.tz.tz import tzutc

from bugwarrior.config import asbool, die
from bugwarrior.services import IssueService, Issue

import logging
log = logging.getLogger(__name__)


# The below `ObliviousCookieJar` and `JIRA` classes are MIT Licensed.
# They were taken from this wonderful commit by @GaretJax
# https://github.com/GaretJax/lancet/commit/f175cb2ec9a2135fb78188cf0b9f621b51d88977
# Prevents Jira web client being logged out when API call is made.
class ObliviousCookieJar(RequestsCookieJar):
    def set_cookie(self, *args, **kwargs):
        """Simply ignore any request to set a cookie."""
        pass

    def copy(self):
        """Make sure to return an instance of the correct class on copying."""
        return ObliviousCookieJar()


class JIRA(BaseJIRA):
    def _create_http_basic_session(self, *args, **kwargs):
        super(JIRA, self)._create_http_basic_session(*args, **kwargs)

        # XXX: JIRA logs the web user out if we send the session cookies we get
        # back from the first request in any subsequent requests. As we don't
        # need cookies when accessing the API anyway, just ignore all of them.
        self._session.cookies = ObliviousCookieJar()

    def close(self):
        self._session.close()


def _parse_sprint_string(sprint):
    """ Parse the big ugly sprint string stored by JIRA.

    They look like:
        com.atlassian.greenhopper.service.sprint.Sprint@4c9c41a5[id=2322,rapid
        ViewId=1173,state=ACTIVE,name=Sprint 1,startDate=2016-09-06T16:08:07.4
        55Z,endDate=2016-09-23T16:08:00.000Z,completeDate=<null>,sequence=2322]
    """
    entries = sprint[sprint.index('[')+1:sprint.index(']')].split('=')
    fields = sum((entry.rsplit(',', 1) for entry in entries), [])
    return dict(zip(fields[::2], fields[1::2]))


class JiraIssue(Issue):
    ISSUE_TYPE = 'jiraissuetype'
    SUMMARY = 'jirasummary'
    URL = 'jiraurl'
    FOREIGN_ID = 'jiraid'
    DESCRIPTION = 'jiradescription'
    ESTIMATE = 'jiraestimate'
    FIX_VERSION = 'jirafixversion'
    CREATED_AT = 'jiracreatedts'
    STATUS = 'jirastatus'

    UDAS = {
        ISSUE_TYPE: {
            'type': 'string',
            'label': 'Issue Type'
        },
        SUMMARY: {
            'type': 'string',
            'label': 'Jira Summary'
        },
        URL: {
            'type': 'string',
            'label': 'Jira URL',
        },
        DESCRIPTION: {
            'type': 'string',
            'label': 'Jira Description',
        },
        FOREIGN_ID: {
            'type': 'string',
            'label': 'Jira Issue ID'
        },
        ESTIMATE: {
            'type': 'numeric',
            'label': 'Estimate'
        },
        FIX_VERSION: {
            'type': 'string',
            'label': 'Fix Version'
        },
        CREATED_AT: {
            'type': 'date',
            'label': 'Created At'
        },
        STATUS: {
            'type': 'string',
            'label': "Jira Status"
        },
    }
    UNIQUE_KEY = (URL, )

    PRIORITY_MAP = {
        'Highest': 'H',
        'High': 'H',
        'Medium': 'M',
        'Low': 'L',
        'Lowest': 'L',
        'Trivial': 'L',
        'Minor': 'L',
        'Major': 'M',
        'Critical': 'H',
        'Blocker': 'H',
    }

    def to_taskwarrior(self):
        return {
            'project': self.get_project(),
            'priority': self.get_priority(),
            'annotations': self.get_annotations(),
            'tags': self.get_tags(),
            'due': self.get_due(),
            'entry': self.get_entry(),

            self.ISSUE_TYPE: self.get_issue_type(),
            self.URL: self.get_url(),
            self.FOREIGN_ID: self.record['key'],
            self.DESCRIPTION: self.record.get('fields', {}).get('description'),
            self.SUMMARY: self.get_summary(),
            self.ESTIMATE: self.get_estimate(),
            self.FIX_VERSION: self.get_fix_version(),
            self.STATUS: self.get_status()
        }

    def get_entry(self):
        created_at = self.record['fields']['created']
        # Convert timestamp to an offset-aware datetime
        date = self.parse_date(created_at).astimezone(tzutc()).replace(microsecond=0)
        return date

    def get_tags(self):
        return self._get_tags_from_labels() + self._get_tags_from_sprints()

    def get_due(self):
        # If the duedate is explicitly set on the issue, then use that.
        if self.record['fields'].get('duedate'):
            return self.parse_date(self.record['fields']['duedate'])
        # Otherwise, if the issue is in a sprint, use the end date of that sprint.
        sprints = self.__get_sprints()
        for sprint in filter(lambda e: e.get('state') != 'CLOSED', sprints):
            endDate = sprint['endDate']
            if endDate != '<null>':
                return self.parse_date(endDate)

    def _get_tags_from_sprints(self):
        tags = []

        if not self.origin['import_sprints_as_tags']:
            return tags

        context = self.record.copy()
        label_template = Template(self.origin['label_template'])

        sprints = self.__get_sprints()
        for sprint in sprints:
            # Extract the name and render it into a label
            context.update({'label': sprint['name'].replace(' ', '')})
            tags.append(label_template.render(context))

        return tags

    def __get_sprints(self):
        fields = self.record.get('fields', {})
        sprints = sum([
            fields.get(key) or []
            for key in self.origin['sprint_field_names']
        ], [])
        for sprint in sprints:
            # Parse this big ugly string.
            yield _parse_sprint_string(sprint)

    def _get_tags_from_labels(self):
        tags = []

        if not self.origin['import_labels_as_tags']:
            return tags

        context = self.record.copy()
        label_template = Template(self.origin['label_template'])

        for label in self.record.get('fields', {}).get('labels', []):
            context.update({'label': label})
            tags.append(label_template.render(context))

        return tags

    def get_annotations(self):
        return self.extra.get('annotations', [])

    def get_project(self):
        return self.record['key'].rsplit('-', 1)[0]

    def get_number(self):
        return self.record['key'].rsplit('-', 1)[1]

    def get_url(self):
        return self.origin['url'] + '/browse/' + self.record['key']

    def get_summary(self):
        if self.extra.get('jira_version') == 4:
            return self.record['fields']['summary']['value']
        return self.record['fields']['summary']

    def get_estimate(self):
        if self.extra.get('jira_version') == 4:
            return self.record['fields']['timeestimate']['value']
        try:
            return self.record['fields']['timeestimate'] / 60 / 60
        except (TypeError, KeyError):
            return None

    def get_priority(self):
        value = self.record['fields'].get('priority')
        try:
            value = value['name']
        except (TypeError, ):
            value = str(value)
        # priority.name format: "1 - Critical"
        map_key = value.strip().split()[-1]
        return self.PRIORITY_MAP.get(map_key, self.origin['default_priority'])

    def get_default_description(self):
        return self.build_default_description(
            title=self.get_summary(),
            url=self.get_processed_url(self.get_url()),
            number=self.get_number(),
            cls='issue',
        )

    def get_fix_version(self):
        try:
            return self.record['fields'].get('fixVersions', [{}])[0].get('name')
        except (IndexError, KeyError, AttributeError, TypeError):
            return None

    def get_status(self):
        return self.record['fields']['status']['name']

    def get_issue_type(self):
        return self.record['fields']['issuetype']['name']


class JiraService(IssueService):
    ISSUE_CLASS = JiraIssue
    CONFIG_PREFIX = 'jira'

    def __init__(self, *args, **kw):
        super(JiraService, self).__init__(*args, **kw)
        self.username = self.config.get('username')
        self.url = self.config.get('base_uri')
        password = self.get_password('password', self.username)

        default_query = 'assignee=' + self.username + \
            ' AND resolution is null'
        self.query = self.config.get('query', default_query)
        if password == '@kerberos':
            auth = dict(kerberos=True)
        else:
            auth = dict(basic_auth=(self.username, password))
        self.jira = JIRA(
            options={
                'server': self.config.get('base_uri'),
                'rest_api_version': 'latest',
                'verify': self.config.get('verify_ssl', default=True, to_type=asbool),
            },
            **auth
        )
        self.import_labels_as_tags = self.config.get(
            'import_labels_as_tags', default=False, to_type=asbool
        )
        self.import_sprints_as_tags = self.config.get(
            'import_sprints_as_tags', default=False, to_type=asbool
        )
        self.label_template = self.config.get(
            'label_template', default='{{label}}', to_type=six.text_type
        )

        self.sprint_field_names = []
        if self.import_sprints_as_tags:
            field_names = [field for field in self.jira.fields()
                           if field['name'] == 'Sprint']
            if len(field_names) < 1:
                log.warn("No sprint custom field found.  Ignoring sprints.")
                self.import_sprints_as_tags = False
            else:
                log.info("Found %i distinct sprint fields." % len(field_names))
                self.sprint_field_names = [field['id'] for field in field_names]

    @staticmethod
    def get_keyring_service(service_config):
        username = service_config.get('username')
        base_uri = service_config.get('base_uri')
        return "jira://%s@%s" % (username, base_uri)

    def get_service_metadata(self):
        return {
            'url': self.url,
            'import_labels_as_tags': self.import_labels_as_tags,
            'import_sprints_as_tags': self.import_sprints_as_tags,
            'sprint_field_names': self.sprint_field_names,
            'label_template': self.label_template,
        }

    @classmethod
    def validate_config(cls, service_config, target):
        for option in ('username', 'password', 'base_uri'):
            if option not in service_config:
                die("[%s] has no 'jira.%s'" % (target, option))

        IssueService.validate_config(service_config, target)

    def annotations(self, issue, issue_obj):
        comments = self.jira.comments(issue.key) or []
        return self.build_annotations(
            ((
                comment.author.name,
                comment.body
            ) for comment in comments),
            issue_obj.get_processed_url(issue_obj.get_url())
        )

    def issues(self):
        cases = self.jira.search_issues(self.query, maxResults=-1)

        jira_version = 5
        if self.config.has_option(self.target, 'jira.version'):
            jira_version = self.config.getint(self.target, 'jira.version')

        for case in cases:
            issue = self.get_issue_for_record(case.raw)
            extra = {
                'jira_version': jira_version,
            }
            if jira_version > 4:
                extra.update({
                    'annotations': self.annotations(case, issue)
                })
            issue.update_extra(extra)
            yield issue
