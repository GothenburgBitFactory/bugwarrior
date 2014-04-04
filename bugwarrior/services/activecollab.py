import itertools
import time

from twiggy import log

import pypandoc
from pyac.library import activeCollab
from bugwarrior.services import IssueService, Issue
from bugwarrior.config import die


class ActiveCollabClient(object):
    def __init__(self, url, key, user_id, projects):
        self.url = url
        self.key = key
        self.user_id = user_id
        self.projects = projects
        self.ac = activeCollab(key=key, url=url, user_id=user_id)

    def get_task_dict(self, project, key, task):
        assigned_task = {
            'project': project
        }
        if task[u'type'] == 'Task':
            # Load Task data
            task_data = self.ac.get_task(task[u'project_id'],
                                         task[u'ticket_id'])
            assignees = task_data[u'assignees']

            for k, v in enumerate(assignees):
                if (
                    (v[u'is_owner'] is True)
                    and (v[u'user_id'] == int(self.user_id))
                ):
                    assigned_task.update(task_data)
                    return assigned_task
        elif task[u'type'] == 'Subtask':
            # Load SubTask data
            assigned_task.update(task)
            return assigned_task

    def get_project_slug(self, permalink):
        project_name = permalink.split('/')[4]
        return project_name

    def get_issue_generator(self, user_id, project_id, project_name):
        user_tasks_data = self.ac.get_project_tasks(project_id)
        if user_tasks_data:
            for key, task in enumerate(user_tasks_data):
                if (
                    (task[u'assignee_id'] == int(self.user_id))
                    and (task[u'completed_on'] is None)
                ):
                    task['project'] = self.get_project_slug(task['permalink'])
                    task['type'] = 'task'
                    yield task

        # Subtasks
        user_subtasks_data = self.ac.get_subtasks(project_id)
        if user_subtasks_data:
            for key, subtask in enumerate(user_subtasks_data):
                if (
                    (subtask[u'assignee_id'] == int(self.user_id))
                    and (subtask[u'completed_on'] is None)
                ):
                    subtask['project'] = self.get_project_slug(
                        subtask['permalink']
                    )
                    subtask['type'] = 'subtask'
                    yield subtask


class ActiveCollabIssue(Issue):
    BODY = 'acbody'
    NAME = 'acname'
    PERMALINK = 'acpermalink'
    TASK_ID = 'actaskid'
    FOREIGN_ID = 'acid'
    PROJECT_ID = 'acprojectid'
    TYPE = 'actype'
    CREATED_ON = 'accreatedon'
    CREATED_BY_ID = 'accreatedbyid'

    UDAS = {
        BODY: {
            'type': 'string',
            'label': 'ActiveCollab Body'
        },
        NAME: {
            'type': 'string',
            'label': 'ActiveCollab Name'
        },
        PERMALINK: {
            'type': 'string',
            'label': 'ActiveCollab Permalink'
        },
        TASK_ID: {
            'type': 'string',
            'label': 'ActiveCollab Task ID'
        },
        FOREIGN_ID: {
            'type': 'string',
            'label': 'ActiveCollab ID',
        },
        PROJECT_ID: {
            'type': 'string',
            'label': 'ActiveCollab Project ID'
        },
        TYPE: {
            'type': 'string',
            'label': 'ActiveCollab Task Type'
        },
        CREATED_ON: {
            'type': 'date',
            'label': 'ActiveCollab Created On'
        },
        CREATED_BY_ID: {
            'type': 'string',
            'label': 'ActiveCollab Created By'
        },
    }
    UNIQUE_KEY = (FOREIGN_ID, )

    def to_taskwarrior(self):
        record = {
            'project': self.record['project'],
            'priority': self.get_priority(),
            self.NAME: self.record.get('name'),
            self.BODY: pypandoc.convert(self.record.get('body'),
                                        'md', format='html'),
            self.PERMALINK: self.record['permalink'],
            self.TASK_ID: self.record.get('task_id'),
            self.PROJECT_ID: self.record['project'],
            self.FOREIGN_ID: self.record['id'],
            self.TYPE: self.record['type'],
            self.CREATED_BY_ID: self.record['created_by_id'],
        }

        if self.record['type'] == 'subtask':
            # Store the parent task ID for subtasks
            record['actaskid'] = self.record['permalink'].split('/')[6]

        due_on = self.record.get('due_on')
        if isinstance(due_on, dict):
            record['due'] = self.parse_date(due_on['mysql'])
        elif due_on is not None:
            record['due'] = due_on

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
        return project_id

    def get_default_description(self):
        return self.build_default_description(
            title=(
                self.record.get('name')
                if self.record.get('name')
                else self.record.get('body')
            ),
            url=self.get_processed_url(self.record['permalink']),
            number=self.record['id'],
            cls=self.record['type'],
        )


class ActiveCollabService(IssueService):
    ISSUE_CLASS = ActiveCollabIssue
    CONFIG_PREFIX = 'activecollab'

    def __init__(self, *args, **kw):
        super(ActiveCollabService, self).__init__(*args, **kw)

        self.url = self.config_get('url').rstrip('/')
        self.key = self.config_get('key')
        self.user_id = self.config_get('user_id')
        self.projects = []
        self.client = ActiveCollabClient(
            self.url, self.key, self.user_id, self.projects
        )
        self.ac = activeCollab(url=self.url, key=self.key,
                               user_id=self.user_id)

        data = self.ac.get_projects()
        for item in data:
            if item[u'is_favorite'] == 1:
                self.projects.append(dict([(item[u'id'], item[u'name'])]))

    @classmethod
    def validate_config(cls, config, target):
        for k in (
            'activecollab.url', 'activecollab.key', 'activecollab.user_id'
        ):
            if not config.has_option(target, k):
                die("[%s] has no '%s'" % (target, k))

        IssueService.validate_config(config, target)

    def issues(self):
        # Loop through each project
        start = time.time()
        issue_generators = []
        projects = self.projects
        for project in projects:
            for project_id, project_name in project.iteritems():
                log.name(self.target).debug(
                    " Getting tasks for #%d %s" % (project_id, project_name)
                )
                issue_generators.append(
                    self.client.get_issue_generator(
                        self.user_id, project_id, project_name
                    )
                )

        log.name(self.target).debug(
            " Elapsed Time: %s" % (time.time() - start))

        for record in itertools.chain(*issue_generators):
            yield self.get_issue_for_record(record)
