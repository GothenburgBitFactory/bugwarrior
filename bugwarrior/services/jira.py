from collections.abc import Iterator
import dataclasses
import datetime
from functools import reduce
import logging
import sys
import typing
from typing import Any

from jira.client import JIRA as BaseJIRA
from jira.exceptions import JIRAError
from pydantic import BeforeValidator, ConfigDict, Field, model_validator
from requests.cookies import RequestsCookieJar

from bugwarrior import config
from bugwarrior.services import Issue, Service
from bugwarrior.task import IssueDatetime, Task, Udas, coerce_datetime

log = logging.getLogger(__name__)


class ExtraFieldConfigError(Exception):
    def __init__(self, extra_field_raw: str) -> None:
        self.message = f'Extra field is improperly defined: {extra_field_raw}'
        super().__init__(self.message)


class ExtraFieldNotFoundError(Exception):
    def __init__(self, label: str, query: str) -> None:
        self.message = f'Extra field {label}:{query} not found among Jira issue fields.'
        super().__init__(self.message)


def parse_jira_extra_fields(extra_fields_raw: Any) -> "list[JiraExtraField] | None":
    if extra_fields_raw is None:
        return None
    try:  # ini
        extra_fields_list = extra_fields_raw.split(',')
    except AttributeError:  # toml
        extra_fields_list = extra_fields_raw
    extra_fields = []
    for extra_field_raw in extra_fields_list:
        split_extra_field = extra_field_raw.strip().split(":", maxsplit=2)

        try:
            label, keys = split_extra_field
        except (IndexError, ValueError):
            raise ExtraFieldConfigError(extra_field_raw)

        keys = keys.split('.')

        extra_field = JiraExtraField(label, keys)
        extra_fields.append(extra_field)
    return extra_fields


@dataclasses.dataclass
class JiraExtraField:
    label: str
    keys: list[str]

    def extract_value(self, fields: dict[str, Any]) -> Any:
        """Extract a field value from a dictionary of Jira issue fields."""

        try:
            value = reduce(
                lambda val, key: val.get(key) if val else None, self.keys, fields
            )
        except KeyError:
            raise ExtraFieldNotFoundError(label=self.label, query='.'.join(self.keys))

        return value


JiraExtraFields = typing.Annotated[
    list[JiraExtraField], BeforeValidator(parse_jira_extra_fields)
]


class JiraConfig(config.ServiceConfig):
    service: typing.Literal['jira']
    KEYRING_SERVICE = "jira://{username}@{base_uri}"
    base_uri: config.StrippedTrailingSlashUrl
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

    only_if_assigned: config.UnsupportedOption[str] = ''
    also_unassigned: config.UnsupportedOption[bool] = False

    @model_validator(mode='after')
    def require_password_xor_PAT(self) -> "JiraConfig":
        if (self.password and self.PAT) or not (self.password or self.PAT):
            raise ValueError(
                'section requires one of (not both):\n    password\n    PAT'
            )
        return self


# The below `ObliviousCookieJar` and `JIRA` classes are MIT Licensed.
# They were taken from this wonderful commit by @GaretJax
# https://github.com/GaretJax/lancet/commit/f175cb2ec9a2135fb78188cf0b9f621b51d88977
# Prevents Jira web client being logged out when API call is made.
class ObliviousCookieJar(RequestsCookieJar):
    def set_cookie(self, *args: Any, **kwargs: Any) -> None:
        """Simply ignore any request to set a cookie."""
        pass

    def copy(self) -> "ObliviousCookieJar":
        """Make sure to return an instance of the correct class on copying."""
        return ObliviousCookieJar()


class JIRA(BaseJIRA):
    def _create_http_basic_session(self, *args: Any, **kwargs: Any) -> None:
        super()._create_http_basic_session(*args, **kwargs)

        # XXX: JIRA logs the web user out if we send the session cookies we get
        # back from the first request in any subsequent requests. As we don't
        # need cookies when accessing the API anyway, just ignore all of them.
        assert self._session is not None
        self._session.cookies = ObliviousCookieJar()

    def close(self) -> None:
        # this is called in a destructor, which may occur before the session
        # has been created, so be resilient to a missing session
        if (session := getattr(self, "_session", None)) is not None:
            session.close()


def _parse_sprint_string(sprint: str) -> dict[str, str]:
    """Parse the big ugly sprint string stored by JIRA.

    They look like:
        com.atlassian.greenhopper.service.sprint.Sprint@4c9c41a5[id=2322,rapid
        ViewId=1173,state=ACTIVE,name=Sprint 1,startDate=2016-09-06T16:08:07.4
        55Z,endDate=2016-09-23T16:08:00.000Z,completeDate=<null>,sequence=2322]
    """
    entries = sprint[sprint.index('[') + 1 : sprint.index(']')].split('=')
    fields = sum((entry.rsplit(',', 1) for entry in entries), [])
    return dict(zip(fields[::2], fields[1::2]))


class JiraUdas(Udas):
    """Service-specific UDAs contributed by Jira.

    A user can turn any Jira field into a UDA with the "extra_fields" option.
    Those names are only known when bugwarrior runs, so extra keys are allowed
    here.
    """

    model_config = ConfigDict(extra='allow')

    __pydantic_extra__: dict[str, Any] = {}

    UNIQUE_KEY = ('jiraurl',)

    jiraissuetype: str = Field(title='Issue Type')
    jirasummary: str = Field(title='Jira Summary')
    jiraurl: str = Field(title='Jira URL')
    jiradescription: str | None = Field(title='Jira Description')
    jiraid: str = Field(title='Jira Issue ID')
    jiraestimate: float | None = Field(title='Estimate')
    jirafixversion: str | None = Field(title='Fix Version')
    # Never populated by the service: the creation timestamp goes to the
    # generic entry field instead. Declared so a user can fill it via
    # "extra_fields", and defaulted so that doing so is not a collision.
    jiracreatedts: IssueDatetime = Field(default=None, title='Created At')
    jirastatus: str = Field(title="Jira Status")
    jirasubtasks: str = Field(title="Jira Subtasks")
    jiraparent: str | None = Field(title='Jira Parent')


class JiraTask(Task):
    udas: JiraUdas


class JiraIssue(Issue):
    PRIORITY_MAP: dict[str, config.Priority] = {
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

    def to_taskwarrior(self) -> JiraTask:
        return JiraTask(
            project=self.get_project(),
            priority=self.get_priority(),
            annotations=self.get_annotations(),
            tags=self.get_tags(),
            due=self.get_due(),
            entry=self.get_entry(),
            udas=JiraUdas(
                jiraissuetype=self.get_issue_type(),
                jiraurl=self.get_url(),
                jiraid=self.record['key'],
                jiradescription=self.extra.get('body'),
                jirasummary=self.get_summary(),
                jiraestimate=self.get_estimate(),
                jirafixversion=self.get_fix_version(),
                jirastatus=self.get_status(),
                jirasubtasks=self.get_subtasks(),
                jiraparent=self.get_parent(),
                **self.get_extra_fields(),
            ),
        )

    def get_extra_fields(self) -> dict[str, Any]:
        if self.config.extra_fields is None:
            return {}

        return {
            extra_field.label: extra_field.extract_value(self.record['fields'])
            for extra_field in self.config.extra_fields
        }

    def get_entry(self) -> datetime.datetime | None:
        created_at = self.record['fields']['created']
        # Convert timestamp to an offset-aware datetime
        return coerce_datetime(created_at)

    def get_tags(self) -> list[str]:
        labels = self.record.get('fields', {}).get('labels', [])
        label_tags = self.get_tags_from_labels(labels)

        sprints = [sprint['name'] for sprint in self.__get_sprints()]
        sprint_tags = (
            self.render_tags_from_labels(sprints)
            if self.config.import_sprints_as_tags
            else []
        )

        return label_tags + sprint_tags

    def get_due(self) -> datetime.datetime | None:
        # If the duedate is explicitly set on the issue, then use that.
        if self.record['fields'].get('duedate'):
            return coerce_datetime(self.record['fields']['duedate'])
        # Otherwise, if the issue is in a sprint, use the end date of that sprint.
        sprints = self.__get_sprints()
        for sprint in filter(lambda e: e.get('state', '').lower() != 'closed', sprints):
            endDate = sprint.get('endDate')
            if endDate != '<null>':
                return coerce_datetime(endDate)

    def __get_sprints(self) -> Iterator[dict[str, Any]]:
        fields = self.record.get('fields', {})
        sprints = sum(
            (fields.get(key) or [] for key in self.extra['sprint_field_names']), []
        )
        for sprint in sprints:
            if isinstance(sprint, dict):
                yield sprint
            else:
                # Backward compatibility for oder Jira versions where
                # python-jira is not able to parse the sprint and returns a
                # string
                yield _parse_sprint_string(sprint)

    def get_annotations(self) -> list[str]:
        return self.extra.get('annotations', [])

    def get_project(self) -> str:
        return self.record['key'].rsplit('-', 1)[0]

    def get_number(self) -> str:
        return self.record['key'].rsplit('-', 1)[1]

    def get_url(self) -> str:
        return self.config.base_uri + '/browse/' + self.record['key']

    def get_summary(self) -> str:
        if self.config.version == 4:
            return self.record['fields']['summary']['value']
        return self.record['fields']['summary']

    def get_estimate(self) -> float | None:
        if self.config.version == 4:
            return self.record['fields']['timeestimate']['value']
        try:
            return self.record['fields']['timeestimate'] / 60 / 60
        except (TypeError, KeyError):
            return None

    def get_priority(self) -> config.Priority:
        value = self.record['fields'].get('priority')
        try:
            value = value['name']
        except (TypeError,):
            value = str(value)
        # priority.name format: "1 - Critical"
        map_key = value.strip().split()[-1]
        return self.PRIORITY_MAP.get(map_key, self.config.default_priority)

    def get_default_description(self) -> str:
        return self.build_default_description(
            title=self.get_summary(),
            url=self.get_url(),
            number=self.get_number(),
            cls='issue',
        )

    def get_fix_version(self) -> str | None:
        try:
            return self.record['fields'].get('fixVersions', [{}])[0].get('name')
        except (IndexError, KeyError, AttributeError, TypeError):
            return None

    def get_status(self) -> str:
        return self.record['fields']['status']['name']

    def get_subtasks(self) -> str:
        return ','.join(
            task['key'] for task in self.record['fields'].get('subtasks', [])
        )

    def get_parent(self) -> str | None:
        try:
            parent = self.record['fields']['parent']['key']
        except (KeyError,):
            return None

        return parent

    def get_issue_type(self) -> str:
        return self.record['fields']['issuetype']['name']


class JiraService(Service):
    API_VERSION = 2.0
    ISSUE_CLASS = JiraIssue
    TASK_SCHEMA = JiraTask
    CONFIG_SCHEMA = JiraConfig

    def __init__(
        self,
        config: JiraConfig,
        main_config: config.MainSectionConfig,
        *,
        _skip_server: bool = False,
    ) -> None:
        super().__init__(config, main_config)

        default_query = (
            'assignee="'
            + self.config.username.replace("@", "\\u0040")
            + '" AND resolution is null'
        )
        self.query = self.config.query or default_query

        if not _skip_server:
            self.jira = self._build_jira_client()

        self.sprint_field_names = []
        if self.config.import_sprints_as_tags:
            field_names = [
                field for field in self.jira.fields() if field['name'] == 'Sprint'
            ]
            if len(field_names) < 1:
                log.warning("No sprint custom field found.  Ignoring sprints.")
                self.config.import_sprints_as_tags = False
            else:
                log.info("Found %i distinct sprint fields." % len(field_names))
                self.sprint_field_names = [field['id'] for field in field_names]

    def _build_jira_client(self) -> JIRA:
        jira_options = {
            'server': self.config.base_uri,
            'rest_api_version': 'latest',
            'verify': self.config.verify_ssl,
        }
        if self.config.PAT:
            pat = self.get_secret('PAT', self.config.username)
            return JIRA(options=jira_options, token_auth=pat)

        password = self.get_secret('password', self.config.username)
        if password == '@kerberos':
            return JIRA(options=jira_options, kerberos=True)
        if self.config.use_cookies:
            return JIRA(options=jira_options, auth=(self.config.username, password))
        return JIRA(options=jira_options, basic_auth=(self.config.username, password))

    def body(self, record: dict[str, Any]) -> str | None:
        body = record.get('fields', {}).get('description')

        if body:
            body = body[: self.config.body_length]

        return body

    def annotations(self, issue: Any, url: str) -> list[str]:
        comments = self.jira.comments(issue.key) or []
        return self.build_annotations(
            ((comment.author.displayName, comment.body) for comment in comments), url
        )

    def issues(self) -> Iterator[Task]:
        try:
            cases = self.jira.search_issues(self.query, maxResults=False)
        except JIRAError:  # Jira Cloud
            cases = self.jira.enhanced_search_issues(self.query, maxResults=False)

        for case in cases:
            extra: dict[str, Any] = {
                'sprint_field_names': self.sprint_field_names,
                'body': self.body(case.raw),
            }
            if self.config.version > 4:
                url = self.config.base_uri + '/browse/' + case.raw['key']
                extra['annotations'] = self.annotations(case, url)
            yield self.process_record(case.raw, extra)
