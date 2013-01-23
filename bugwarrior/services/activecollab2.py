from twiggy import log

from bugwarrior.services import IssueService
from bugwarrior.config import die
from bugwarrior.db import MARKUP
from HTMLParser import HTMLParser

import urllib2
import time
import json
import datetime


class MLStripper(HTMLParser):
    def __init__(self):
        self.reset()
        self.fed = []

    def handle_data(self, d):
        self.fed.append(d)

    def get_data(self):
        return ''.join(self.fed)


class Client(object):
    def __init__(self, url, key, user_id, projects):
        self.url = url
        self.key = key
        self.user_id = user_id
        self.projects = projects

    def find_issues(self, user_id=None, project_id=None, project_name=None):
        """
        Approach:

        1. Get user ID from .bugwarriorrc file
        2. Get list of tickets from /user-tasks for a given project
        3. For each ticket/task returned from #2, get ticket/task info and check
           if logged-in user is primary (look at `is_owner` and `user_id`)
        """

        user_tasks_data = self.call_api("/projects/" + str(project_id) + "/user-tasks")

        assigned_tasks = []

        for key, task in enumerate(user_tasks_data):
            assigned_task = dict()
            if task[u'type'] == 'Ticket':
                # Load Ticket data
                ticket_data = self.call_api("/projects/" + str(task[u'project_id']) + "/tickets/" + str(task[u'ticket_id']))
                assignees = ticket_data[u'assignees']

                for k, v in enumerate(assignees):
                    if (v[u'is_owner'] is True) and (v[u'user_id'] == int(self.user_id)):
                        assigned_task['permalink'] = ticket_data[u'permalink']
                        assigned_task['ticket_id'] = ticket_data[u'ticket_id']
                        assigned_task['project_id'] = ticket_data[u'project_id']
                        assigned_task['project'] = project_name
                        assigned_task['description'] = ticket_data[u'name']
                        assigned_task['type'] = "ticket"
                        assigned_task['comments'] = ticket_data[u'comments']

            elif task[u'type'] == 'Task':
                # Load Task data
                assigned_task['permalink'] = task[u'permalink']
                assigned_task['project'] = project_name
                assigned_task['description'] = task[u'body']
                assigned_task['project_id'] = task[u'project_id']
                assigned_task['ticket_id'] = ""
                assigned_task['type'] = "task"

            if assigned_task:
                log.debug("Adding '" + assigned_task['description'] + "' to issue list")
                assigned_tasks.append(assigned_task)

        log.debug(" Found {0} total.", len(assigned_tasks))
        return assigned_tasks

    def call_api(self, uri, get=None):
        url = self.url.rstrip("/") + "?token=" + self.key + "&path_info=" + uri + "&format=json"
        req = urllib2.Request(url)
        res = urllib2.urlopen(req)

        return json.loads(res.read())


class ActiveCollab2Service(IssueService):
    def __init__(self, *args, **kw):
        super(ActiveCollab2Service, self).__init__(*args, **kw)

        self.url = self.config.get(self.target, 'url').rstrip("/")
        self.key = self.config.get(self.target, 'key')
        self.user_id = self.config.get(self.target, 'user_id')

        # Make a dictionary of projects
        projects_raw = str(self.config.get(self.target, 'projects'))
        projects_list = projects_raw.split(', ')
        projects = []
        for k, v in enumerate(projects_list):
            project_data = v.split(":")
            project = dict([(project_data[0], project_data[1])])
            projects.append(project)

        self.projects = projects

        self.client = Client(self.url, self.key, self.user_id, self.projects)

    @classmethod
    def validate_config(cls, config, target):
        for k in ('url', 'key', 'projects', 'user_id'):
            if not config.has_option(target, k):
                die("[%s] has no '%s'" % (target, k))

        IssueService.validate_config(config, target)

    def get_issue_url(self, issue):
        return issue['permalink']

    def get_project_name(self, issue):
        return issue['project']

    def description(self, title, project_id, url, ticket_id="", cls="ticket"):

        cls_markup = {
            'ticket': '#',
            'task': 'Task',
        }

        # TODO -- get the '35' here from the config.
        return "%s%s%s - %s .. %s" % (
            MARKUP, cls_markup[cls], str(ticket_id),
            title[:35], self.shorten(url),
        )

    def strip_tags(html):
        s = MLStripper()
        s.feed(html)
        return s.get_data()

    def annotations(self, issue):
        if issue['type'] == 'ticket':
            comments = issue[u'comments']
            return dict([
                self.format_annotation(
                    datetime.datetime.fromtimestamp(time.mktime(time.strptime(
                        c['created_on'], "%Y-%m-%d %H:%M:%S"))),
                    c['created_by_id'],
                    self.strip_tags(c['body']),
                ) for c in comments])
        else:
            return dict()

    def issues(self):
        # Loop through each project
        start = time.time()
        issues = []
        projects = self.projects
        for project in projects:
            for project_id, project_name in project.iteritems():
                log.debug("Getting tasks for #" + project_id + " " + project_name + '"')
                issues += self.client.find_issues(self.user_id, project_id, project_name)

        log.debug(" Found {0} total.", len(issues))

        log.debug("Elapsed Time: %s" % (time.time() - start))

        return [dict(
            description=self.description(
                issue["description"],
                issue["project_id"], issue['permalink'], issue["ticket_id"], issue["type"],
            ),
            project=self.get_project_name(issue),
            priority=self.default_priority
        ) for issue in issues]
