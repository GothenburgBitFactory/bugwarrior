import itertools
import json
import time
import urllib2

import six
from twiggy import log

from bugwarrior.services import IssueService, Issue
from bugwarrior.config import die


class ActiveCollab2Client(object):
    def __init__(self, url, key, user_id, projects):
        self.url = url
        self.key = key
        self.user_id = user_id
        self.projects = projects

    def get_task_dict(self, project, key, task):
        assigned_task = {
            'project': project
        }
        if task[u'type'] == 'Ticket':
            # Load Ticket data
            # @todo Implement threading here.
            ticket_data = self.call_api(
                "/projects/" + six.text_type(task[u'project_id']) +
                "/tickets/" + six.text_type(task[u'ticket_id']))
            assignees = ticket_data[u'assignees']

            for k, v in enumerate(assignees):
                if (
                    (v[u'is_owner'] is True)
                    and (v[u'user_id'] == int(self.user_id))
                ):
                    assigned_task.update(ticket_data)
                    return assigned_task
        elif task[u'type'] == 'Task':
            # Load Task data
            assigned_task.update(task)
            return assigned_task

    def get_issue_generator(self, user_id, project_id, project_name):
        """
        Approach:

        1. Get user ID from bugwarriorrc file
        2. Get list of tickets from /user-tasks for a given project
        3. For each ticket/task returned from #2, get ticket/task info and
           check if logged-in user is primary (look at `is_owner` and
           `user_id`)
        """

        user_tasks_data = self.call_api(
            "/projects/" + six.text_type(project_id) + "/user-tasks")

        for key, task in enumerate(user_tasks_data):

            assigned_task = self.get_task_dict(project_id, key, task)

            if assigned_task:
                log.name(self.target).debug(
                    " Adding '" + assigned_task['description'] +
                    "' to task list.")
                yield assigned_task

    def call_api(self, uri, get=None):
        url = self.url.rstrip("/") + "?token=" + self.key + \
            "&path_info=" + uri + "&format=json"
        req = urllib2.Request(url)
        res = urllib2.urlopen(req)

        return json.loads(res.read())


class ActiveCollab2Issue(Issue):
    BODY = 'ac2body'
    NAME = 'ac2name'
    PERMALINK = 'ac2permalink'
    TICKET_ID = 'ac2ticketid'
    PROJECT_ID = 'ac2projectid'
    TYPE = 'ac2type'
    CREATED_ON = 'ac2createdon'
    CREATED_BY_ID = 'ac2createdbyid'

    UDAS = {
        BODY: {
            'type': 'string',
            'label': 'ActiveCollab2 Body'
        },
        NAME: {
            'type': 'string',
            'label': 'ActiveCollab2 Name'
        },
        PERMALINK: {
            'type': 'string',
            'label': 'ActiveCollab2 Permalink'
        },
        TICKET_ID: {
            'type': 'string',
            'label': 'ActiveCollab2 Ticket ID'
        },
        PROJECT_ID: {
            'type': 'string',
            'label': 'ActiveCollab2 Project ID'
        },
        TYPE: {
            'type': 'string',
            'label': 'ActiveCollab2 Task Type'
        },
        CREATED_ON: {
            'type': 'date',
            'label': 'ActiveCollab2 Created On'
        },
        CREATED_BY_ID: {
            'type': 'string',
            'label': 'ActiveCollab2 Created By'
        },
    }
    UNIQUE_KEY = (PERMALINK, )

    PRIORITY_MAP = {
        -2: 'L',
        -1: 'L',
        0: 'M',
        1: 'H',
        2: 'H',
    }

    def to_taskwarrior(self):
        record = {
            'project': self.record['project'],
            'priority': self.get_priority(),
            'due': self.parse_date(self.record.get('due_on')),

            self.PERMALINK: self.record['permalink'],
            self.TICKET_ID: self.record['ticket_id'],
            self.PROJECT_ID: self.record['project_id'],
            self.TYPE: self.record['type'],
            self.CREATED_ON: self.parse_date(self.record.get('created_on')),
            self.CREATED_BY_ID: self.record['created_by_id'],
            self.BODY: self.record.get('body'),
            self.NAME: self.record.get('name'),
        }
        return record

    def get_default_description(self):
        return self.build_default_description(
            title=(
                self.record['name']
                if self.record['name']
                else self.record['body']
            ),
            url=self.get_processed_url(self.record['permalink']),
            number=self.record['ticket_id'],
            cls=self.record['type'].lower(),
        )


class ActiveCollab2Service(IssueService):
    ISSUE_CLASS = ActiveCollab2Issue
    CONFIG_PREFIX = 'activecollab2'

    def __init__(self, *args, **kw):
        super(ActiveCollab2Service, self).__init__(*args, **kw)

        self.url = self.config_get('url').rstrip('/')
        self.key = self.config_get('key')
        self.user_id = self.config_get('user_id')
        projects_raw = self.config_get('projects')

        projects_list = projects_raw.split(',')
        projects = []
        for k, v in enumerate(projects_list):
            project_data = v.strip().split(":")
            project = dict([(project_data[0], project_data[1])])
            projects.append(project)

        self.projects = projects

        self.client = ActiveCollab2Client(
            self.url, self.key, self.user_id, self.projects
        )

    @classmethod
    def validate_config(cls, config, target):
        for k in (
            'activecollab2.url',
            'activecollab2.key',
            'activecollab2.projects',
            'activecollab2.user_id'
        ):
            if not config.has_option(target, k):
                die("[%s] has no '%s'" % (target, k))

        super(ActiveCollab2Service, cls).validate_config(config, target)

    def issues(self):
        # Loop through each project
        start = time.time()
        issue_generators = []
        projects = self.projects
        for project in projects:
            for project_id, project_name in project.iteritems():
                log.name(self.target).debug(
                    " Getting tasks for #" + project_id +
                    " " + project_name + '"')
                issue_generators.append(
                    self.client.get_issue_generator(
                        self.user_id, project_id, project_name
                    )
                )

        log.name(self.target).debug(
            " Elapsed Time: %s" % (time.time() - start))

        for record in itertools.chain(*issue_generators):
            yield self.get_issue_for_record(record)
