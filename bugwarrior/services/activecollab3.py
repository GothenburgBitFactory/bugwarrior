import json
import re
import urllib2

from bugwarrior.services import IssueService
from bugwarrior.config import die

from .activecollab2 import (
    ActiveCollab2Client,
    ActiveCollab2Issue,
    ActiveCollab2Service,
)


class ActiveCollab3Client(ActiveCollab2Client):
    def get_project_slug(self, project_name):
        # Take a project name like "Client: Example Project" and return a
        # string in project slug format: "client-example-project"
        project_name = project_name.lower()
        project_name = re.sub('[\s+]', '-', project_name)
        project_name = re.sub('[:,"/"]', '', project_name)
        return project_name

    def call_api(self, uri, key, url):
        url = url.rstrip("/") + "?auth_api_token=" + key + \
            "&path_info=" + uri + "&format=json"
        req = urllib2.Request(url)
        res = urllib2.urlopen(req)
        return json.loads(res.read())

    def get_issue_generator(self, user_id, project_id, project_name):
        user_tasks_data = self.call_api(
            "/projects/" + str(project_id) + "/tasks", self.key, self.url
        )
        if user_tasks_data:
            for key, task in enumerate(user_tasks_data):
                if (
                    (task[u'assignee_id'] == int(self.user_id))
                    and (task[u'completed_on'] is None)
                ):
                    task['project'] = self.get_project_slug(project_name)
                    task['type'] = 'task'
                    yield task

        # Subtasks
        user_subtasks_data = self.call_api(
            "/projects/" + str(project_id) + "/subtasks", self.key, self.url
        )
        if user_subtasks_data:
            for key, subtask in enumerate(user_subtasks_data):
                if (
                    (subtask[u'assignee_id'] == int(self.user_id))
                    and (subtask[u'completed_on'] is None)
                ):
                    subtask['project'] = self.get_project_slug(project_name)
                    subtask['type'] = 'subtask'
                    yield subtask


class ActiveCollab3Issue(ActiveCollab2Issue):
    BODY = 'ac3body'
    NAME = 'ac3name'
    PERMALINK = 'ac3permalink'
    TASK_ID = 'ac3taskid'
    FOREIGN_ID = 'ac3id'
    PROJECT_ID = 'ac3projectid'
    TYPE = 'ac3type'
    CREATED_ON = 'ac3createdon'
    CREATED_BY_ID = 'ac3createdbyid'

    UDAS = {
        BODY: {
            'type': 'string',
            'label': 'ActiveCollab3 Body'
        },
        NAME: {
            'type': 'string',
            'label': 'ActiveCollab3 Name'
        },
        PERMALINK: {
            'type': 'string',
            'label': 'ActiveCollab3 Permalink'
        },
        TASK_ID: {
            'type': 'string',
            'label': 'ActiveCollab3 Task ID'
        },
        FOREIGN_ID: {
            'type': 'string',
            'label': 'ActiveCollab3 ID',
        },
        PROJECT_ID: {
            'type': 'string',
            'label': 'ActiveCollab3 Project ID'
        },
        TYPE: {
            'type': 'string',
            'label': 'ActiveCollab3 Task Type'
        },
        CREATED_ON: {
            'type': 'date',
            'label': 'ActiveCollab3 Created On'
        },
        CREATED_BY_ID: {
            'type': 'string',
            'label': 'ActiveCollab3 Created By'
        },
    }
    UNIQUE_KEY = (PERMALINK, )

    def to_taskwarrior(self):
        record = {
            'project': self.record['project'],
            'priority': self.get_priority(),
            'due': self.parse_date(self.record.get('due_on')),

            self.NAME: self.record.get('name'),
            self.BODY: self.record.get('body'),
            self.PERMALINK: self.record['permalink'],
            self.TASK_ID: self.record.get('task_id'),
            self.PROJECT_ID: self.record['project_id'],
            self.FOREIGN_ID: self.record['id'],
            self.TYPE: self.record['type'],
            self.CREATED_BY_ID: self.record['created_by_id'],
        }
        if isinstance(self.record.get('created_on'), basestring):
            record[self.CREATED_ON] = self.parse_date(
                self.record['created_on']
            )
        elif isinstance(
            self.record.get('created_on', {}).get('mysql'), basestring
        ):
            record[self.CREATED_ON] = self.parse_date(
                self.record['created_on']['mysql']
            )
        return record

    def get_project(self):
        project_id = self.record['permalink'].split('/')[4]
        if (project_id.isdigit()):
            return self.record['project']
        else:
            return project_id

    def get_default_description(self):
        return self.build_default_description(
            title=(
                self.record['name']
                if self.record['name']
                else self.record['body']
            ),
            url=self.record['permalink'],
            number=self.record['id'],
            cls=self.record['type'],
        )


class ActiveCollab3Service(ActiveCollab2Service):
    ISSUE_CLASS = ActiveCollab3Issue
    CONFIG_PREFIX = 'activecollab3'

    def __init__(self, *args, **kw):
        super(ActiveCollab3Service, self).__init__(*args, **kw)
        self.client = ActiveCollab3Client(
            self.url, self.key, self.user_id, self.projects
        )

        self.projects = []
        data = self.client.call_api("/projects", self.key, self.url)
        for item in data:
            if item[u'is_favorite'] == 1:
                self.projects.append(dict([(item[u'id'], item[u'name'])]))

    @classmethod
    def validate_config(cls, config, target):
        for k in (
            'activecollab3.url', 'activecollab3.key', 'activecollab3.user_id'
        ):
            if not config.has_option(target, k):
                die("[%s] has no '%s'" % (target, k))

        IssueService.validate_config(config, target)
