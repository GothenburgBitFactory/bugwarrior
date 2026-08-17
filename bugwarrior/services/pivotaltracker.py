from collections.abc import Iterator
import logging
import operator
import re
import typing
from typing import Any

from jinja2 import Template
from pydantic import Field
import requests

from bugwarrior import config
from bugwarrior.services import Client, Issue, Service
from bugwarrior.task import IssueDatetime, Task, Udas

log = logging.getLogger(__name__)


class PivotalTrackerConfig(config.ServiceConfig):
    service: typing.Literal['pivotaltracker']
    KEYRING_SERVICE = 'pivotaltracker://{user_id}@{host}'
    user_id: int
    account_ids: config.ConfigList
    token: str

    version: typing.Literal['v5', 'edge'] = 'v5'
    host: config.StrippedTrailingSlashUrl = 'https://www.pivotaltracker.com/services'
    exclude_projects: config.ConfigList = []
    exclude_stories: config.ConfigList = []
    exclude_tags: config.ConfigList = []
    import_blockers: bool = True
    blocker_template: str = 'Description: {{description}} State: {{resolved}}\n'
    import_labels_as_tags: bool = False
    label_template: str = "{{label|replace(' ', '_')}}"
    annotation_template: str = 'status: {{complete}} - {{description}}'
    only_if_author: bool = False
    query: str = ''

    # XXX Override common configuration option
    only_if_assigned: bool = True


class PivotalTrackerUdas(Udas):
    """Service-specific UDAs contributed by PivotalTracker."""

    UNIQUE_KEY = ('pivotalurl',)

    pivotalurl: str = Field(title='Story URL')
    pivotaldescription: str | None = Field(title='Story Description')
    pivotalstorytype: str = Field(title='Story Type')
    pivotalprojectid: int = Field(title='Project ID')
    pivotalprojectname: str = Field(title='Project Name')
    pivotalid: int = Field(title='Story ID')
    pivotalowners: str | None = Field(title='Story Owned By')
    pivotalrequesters: str | None = Field(title='Story Requested By')
    pivotalestimate: int = Field(title='Story Estimate')
    pivotalblockers: str | None = Field(title='Story Blockers')
    pivotalcreated: IssueDatetime = Field(title='Story Created')
    pivotalupdated: IssueDatetime = Field(title='Story Updated')
    pivotalclosed: IssueDatetime = Field(title='Story Closed')


class PivotalTrackerTask(Task):
    udas: PivotalTrackerUdas


class PivotalTrackerIssue(Issue):
    def to_taskwarrior(self) -> PivotalTrackerTask:
        return PivotalTrackerTask(
            project=re.sub(r'[^a-zA-Z0-9]', '_', self.extra['project_name']).lower(),
            priority=self.config.default_priority,
            annotations=self.extra.get('annotations', []),
            tags=self.get_tags(),
            udas=PivotalTrackerUdas(
                pivotalurl=self.record['url'],
                pivotaldescription=self.record.get('description'),
                pivotalstorytype=self.record['story_type'],
                pivotalprojectid=self.record['project_id'],
                pivotalprojectname=self.extra['project_name'],
                pivotalid=self.record['id'],
                pivotalowners=self.extra['owned_user'],
                pivotalrequesters=self.extra['request_user'],
                # int() truncates: a fractional point scale would
                # otherwise be rejected rather than rounded down.
                pivotalestimate=int(self.record.get('estimate', 0)),
                pivotalblockers=self.extra['blockers'],
                pivotalcreated=self.record.get('created_at'),
                pivotalupdated=self.record.get('updated_at'),
                pivotalclosed=self.record.get('accepted_at'),
            ),
        )

    def get_tags(self) -> list[str]:
        labels = [label['name'] for label in self.record.get('labels', [])]
        return self.get_tags_from_labels(labels)

    def get_default_description(self) -> str:
        return self.build_default_description(
            title=self.record.get('name', ''),
            url=self.record.get('url', ''),
            number=int(self.record['id']),
            cls=self.record.get('story_type', 'issue'),
        )


class PivotalTrackerService(Service):
    API_VERSION = 2.0
    ISSUE_CLASS = PivotalTrackerIssue
    TASK_SCHEMA = PivotalTrackerTask
    CONFIG_SCHEMA = PivotalTrackerConfig

    def __init__(
        self, config: PivotalTrackerConfig, main_config: config.MainSectionConfig
    ) -> None:
        super().__init__(config, main_config)

        self.path = f"{self.config.host}/{self.config.version}"

        self.session = requests.Session()
        self.session.headers.update(
            {'X-TrackerToken': self.config.token, 'Content-Type': 'application/json'}
        )

        self.query = self.config.query

        if not self.query:
            if self.config.only_if_assigned and not self.config.also_unassigned:
                self.query += f"mywork:{self.config.user_id}"
            if self.config.exclude_stories:
                self.query += " -id:{stories}".format(
                    stories=",".join(self.config.exclude_stories)
                )
            if self.config.exclude_tags:
                self.query += " -label:{labels}".format(
                    labels=",".join(self.config.exclude_tags)
                )
            if self.config.only_if_author:
                self.query += f" requester:{self.config.user_id}"

    def annotations(
        self, annotations: list[dict[str, Any]], story: dict[str, Any]
    ) -> list[str]:
        final_annotations = []
        if self.main_config.annotation_comments:
            annotation_template = Template(self.config.annotation_template)
            for annotation in annotations:
                final_annotations.append(
                    ('task', annotation_template.render(annotation))
                )
        return self.build_annotations(final_annotations, story.get('url'))

    def blockers(self, blocker_list: list[dict[str, Any]]) -> str | None:
        blockers = []

        if not self.config.import_blockers:
            return None

        blocker_template = Template(self.config.blocker_template)
        for blocker in blocker_list:
            blockers.append(blocker_template.render(blocker))

        return ', '.join(blockers) or None

    def issues(self) -> Iterator[Task]:
        for project in self.get_projects(self.config.account_ids):
            project_id = project.get('id')
            if project_id is None or project_id in self.config.exclude_projects:
                continue

            for story in self.get_query(project_id, query=self.query):
                story_id = story.get('id')
                if story_id is None:
                    continue
                tasks = self.get_tasks(project_id, story_id)
                blockers = self.get_blockers(project_id, story_id)
                extra = {
                    'project_name': project.get('name'),
                    'annotations': self.annotations(tasks, story),
                    'owned_user': self.get_user_by_id(project_id, story['owner_ids']),
                    'request_user': self.get_user_by_id(
                        project_id, [story['requested_by_id']]
                    ),
                    'blockers': self.blockers(blockers),
                }
                yield self.process_record(story, extra)

    def api_request(self, endpoint: str, params: dict[str, Any] | None = None) -> Any:
        """
        Make a PivotalTracker API request. This takes an absolute urland a list
        of argumnets and return a GET request with the key and token from the
        configuration.
        """

        response = self.session.get(f"{self.path}/{endpoint}", params=params or {})
        return Client.json_response(response)

    def get_projects(self, account_ids: list[str]) -> list[dict[str, Any]]:
        params = {'account_ids': ','.join(account_ids)}
        projects = self.api_request('projects', params=params)
        return projects

    def get_query(self, project_id: str | int, **params: Any) -> list[dict[str, Any]]:
        query = self.api_request(f"projects/{project_id}/search", params=params)
        return query['stories']['stories']

    def get_tasks(
        self, project_id: str | int, story_id: str | int
    ) -> list[dict[str, Any]]:
        tasks = self.api_request(f"projects/{project_id}/stories/{story_id}/tasks")
        return tasks

    def get_blockers(
        self, project_id: str | int, story_id: str | int
    ) -> list[dict[str, Any]]:
        blockers = self.api_request(
            f"projects/{project_id}/stories/{story_id}/blockers"
        )
        blocker_results = []
        for blocker in blockers:
            blocker['users'] = self.get_user_by_id(project_id, [blocker['person_id']])
            blocker_results.append(blocker)
        return blocker_results

    def get_user_by_id(self, project_id: str | int, user_ids: list[Any]) -> str | None:
        persons = self.api_request(f"projects/{project_id}/memberships")
        user_list = filter(
            lambda x: x.get('id') in user_ids,
            map(operator.itemgetter('person'), persons),
        )
        return ', '.join(list(map(operator.itemgetter('username'), user_list))) or None
