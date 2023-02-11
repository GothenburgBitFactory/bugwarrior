import logging
import sys
import typing
from functools import reduce

import pydantic
import typing_extensions
from dateutil.tz.tz import tzutc
from jira.client import JIRA as BaseJIRA
from requests.cookies import RequestsCookieJar

from bugwarrior import config
from bugwarrior.services import Issue, IssueService

log = logging.getLogger(__name__)


class ExtraFieldConfigError(Exception):
    def __init__(self, extra_field_raw):
        self.message = f'Extra field is improperly defined: {extra_field_raw}'
        super().__init__(self.message)


class ExtraFieldNotFoundError(Exception):
    def __init__(self, label, query):
        self.message = f'Extra field {label}:{query} not found among Jira issue fields.'
        super().__init__(self.message)


class JiraExtraFields(frozenset):

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, extra_fields_raw):
        try:  # ini
            extra_fields_list = extra_fields_raw.split(',')
        except AttributeError:  # toml
            extra_fields_list = extra_fields_raw
        extra_fields = []
        for extra_field_raw in extra_fields_list:
            split_extra_field = extra_field_raw.strip().split(":", maxsplit=2)

            try:
                label, keys = split_extra_field
            except IndexError:
                raise ExtraFieldConfigError(extra_field_raw)

            keys = keys.split('.')

            extra_field = JiraExtraField(label, keys)
            extra_fields.append(extra_field)
        return extra_fields


# NOTE: replace with stdlib dataclasses.dataclass once python-3.6 is dropped
@pydantic.dataclasses.dataclass
class JiraExtraField:
    label: str
    keys: typing.List[str]

    def extract_value(self, fields):
        """Extract a field value from a dictionary of Jira issue fields."""

        try:
            value = reduce(
                lambda val, key: val.get(key) if val else None,
                self.keys,
                fields)
        except KeyError:
            raise ExtraFieldNotFoundError(
                label=self.label, query='.'.join(self.keys))

        return value


class JiraConfig(config.ServiceConfig):
    service: typing_extensions.Literal['jira']
    base_uri: pydantic.AnyUrl
    username: str

    password: str = ''
    PAT: str = ''

    body_length: int = sys.maxsize
    extra_fields: typing.Optional[JiraExtraFields] = None
    import_labels_as_tags: bool = False
    import_sprints_as_tags: bool = False
    label_template: str = '{{label}}'
    query: str = ''
    use_cookies: bool = False
    verify_ssl: bool = True
    version: int = 5

    @pydantic.root_validator
    def require_password_xor_PAT(cls, values):
        if ((values['password'] and values['PAT'])
                or not (values['password'] or values['PAT'])):
            raise ValueError(
                'section requires one of (not both):\n    password\n    PAT')
        return values


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
        super()._create_http_basic_session(*args, **kwargs)

        # XXX: JIRA logs the web user out if we send the session cookies we get
        # back from the first request in any subsequent requests. As we don't
        # need cookies when accessing the API anyway, just ignore all of them.
        self._session.cookies = ObliviousCookieJar()

    def close(self):
        # this is called in a destructor, which may occur before the session
        # has been created, so be resilient to a missing session
        if hasattr(self, "_session"):
            self._session.close()


def _parse_sprint_string(sprint):
    """ Parse the big ugly sprint string stored by JIRA.

    They look like:
        com.atlassian.greenhopper.service.sprint.Sprint@4c9c41a5[id=2322,rapid
        ViewId=1173,state=ACTIVE,name=Sprint 1,startDate=2016-09-06T16:08:07.4
        55Z,endDate=2016-09-23T16:08:00.000Z,completeDate=<null>,sequence=2322]
    """
    entries = sprint[sprint.index('[') + 1:sprint.index(']')].split('=')
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
    SUBTASKS = 'jirasubtasks'
    PARENT = 'jiraparent'

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
        SUBTASKS: {
            'type': 'string',
            'label': "Jira Subtasks"
        },
        PARENT: {
            'type': 'string',
            'label': 'Jira Parent'
        }
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
        fixed_fields = {
            'project': self.get_project(),
            'priority': self.get_priority(),
            'annotations': self.get_annotations(),
            'tags': self.get_tags(),
            'due': self.get_due(),
            'entry': self.get_entry(),

            self.ISSUE_TYPE: self.get_issue_type(),
            self.URL: self.get_url(),
            self.FOREIGN_ID: self.record['key'],
            self.DESCRIPTION: self.extra.get('body'),
            self.SUMMARY: self.get_summary(),
            self.ESTIMATE: self.get_estimate(),
            self.FIX_VERSION: self.get_fix_version(),
            self.STATUS: self.get_status(),
            self.SUBTASKS: self.get_subtasks(),
            self.PARENT: self.get_parent(),
        }

        extra_fields = self.get_extra_fields()

        return {**fixed_fields, **extra_fields}

    def get_extra_fields(self):
        if self.extra['extra_fields'] is None:
            return {}

        return {extra_field.label: extra_field.extract_value(
            self.record['fields']) for extra_field in self.extra['extra_fields']}

    def get_entry(self):
        created_at = self.record['fields']['created']
        # Convert timestamp to an offset-aware datetime
        date = self.parse_date(created_at).astimezone(
            tzutc()).replace(microsecond=0)
        return date

    def get_tags(self):
        labels = self.record.get('fields', {}).get('labels', [])
        label_tags = self.get_tags_from_labels(labels)

        sprints = [sprint['name'] for sprint in self.__get_sprints()]
        sprint_tags = self.get_tags_from_labels(
            sprints, toggle_option='import_sprints_as_tags')

        return label_tags + sprint_tags

    def get_due(self):
        # If the duedate is explicitly set on the issue, then use that.
        if self.record['fields'].get('duedate'):
            return self.parse_date(self.record['fields']['duedate'])
        # Otherwise, if the issue is in a sprint, use the end date of that sprint.
        sprints = self.__get_sprints()
        for sprint in filter(lambda e: e.get('state', '').lower() != 'closed', sprints):
            endDate = sprint['endDate']
            if endDate != '<null>':
                return self.parse_date(endDate)

    def __get_sprints(self):
        fields = self.record.get('fields', {})
        sprints = sum((
            fields.get(key) or []
            for key in self.origin['sprint_field_names']
        ), [])
        for sprint in sprints:
            if isinstance(sprint, dict):
                yield sprint
            else:
                # Backward compatibility for oder Jira versions where
                # python-jira is not able to parse the sprint and returns a
                # string
                yield _parse_sprint_string(sprint)

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

    def get_subtasks(self):
        return ','.join(task['key'] for task in self.record['fields'].get('subtasks', []))

    def get_parent(self):
        try:
            parent = self.record['fields']['parent']['key']
        except (KeyError, ):
            return None

        return parent

    def get_issue_type(self):
        return self.record['fields']['issuetype']['name']


class JiraService(IssueService):
    ISSUE_CLASS = JiraIssue
    CONFIG_SCHEMA = JiraConfig

    def __init__(self, *args, **kw):
        _skip_server = kw.pop('_skip_server', False)
        super().__init__(*args, **kw)

        default_query = 'assignee="' + \
            self.config.username.replace("@", "\\u0040") + \
            '" AND resolution is null'
        self.query = self.config.query or default_query

        if self.config.PAT:
            pat = self.get_password('PAT', self.config.username)
            auth = dict(token_auth=pat)
        else:
            password = self.get_password('password', self.config.username)
            if password == '@kerberos':
                auth = dict(kerberos=True)
            else:
                if self.config.use_cookies:
                    auth = dict(auth=(self.config.username, password))
                else:
                    auth = dict(basic_auth=(self.config.username, password))
        if not _skip_server:
            self.jira = JIRA(
                options={
                    'server': self.config.base_uri,
                    'rest_api_version': 'latest',
                    'verify': self.config.verify_ssl,
                },
                **auth
            )
        self.import_sprints_as_tags = self.config.import_sprints_as_tags

        self.sprint_field_names = []
        if self.import_sprints_as_tags:
            field_names = [field for field in self.jira.fields()
                           if field['name'] == 'Sprint']
            if len(field_names) < 1:
                log.warn("No sprint custom field found.  Ignoring sprints.")
                self.import_sprints_as_tags = False
            else:
                log.info("Found %i distinct sprint fields." % len(field_names))
                self.sprint_field_names = [field['id']
                                           for field in field_names]

    @staticmethod
    def get_keyring_service(config):
        return f"jira://{config.username}@{config.base_uri}"

    def get_service_metadata(self):
        return {
            'url': self.config.base_uri,
            'import_labels_as_tags': self.config.import_labels_as_tags,
            'import_sprints_as_tags': self.import_sprints_as_tags,
            'sprint_field_names': self.sprint_field_names,
            'label_template': self.config.label_template,
        }

    def get_owner(self, issue):
        # TODO
        raise NotImplementedError(
            "This service has not implemented support for 'only_if_assigned'.")

    def body(self, issue):
        body = issue.record.get('fields', {}).get('description')

        if body:
            body = body[:self.config.body_length]

        return body

    def annotations(self, issue, issue_obj):
        comments = self.jira.comments(issue.key) or []
        return self.build_annotations(
            ((
                comment.author.displayName,
                comment.body
            ) for comment in comments),
            issue_obj.get_processed_url(issue_obj.get_url())
        )

    def issues(self):
        cases = self.jira.search_issues(self.query, maxResults=None)

        for case in cases:
            issue = self.get_issue_for_record(case.raw)
            extra = {
                'jira_version': self.config.version,
                'body': self.body(issue),
                'extra_fields': self.config.extra_fields,
            }
            if self.config.version > 4:
                extra.update({
                    'annotations': self.annotations(case, issue)
                })
            issue.update_extra(extra)
            yield issue
