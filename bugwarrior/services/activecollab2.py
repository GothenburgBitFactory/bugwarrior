from twiggy import log

from bugwarrior.services import IssueService
from bugwarrior.config import die
from bugwarrior.db import MARKUP

import urllib2
import time
import json
import datetime

api_count = 0
task_count = 0


class Client(object):
    def __init__(self, url, key, user_id, projects):
        self.url = url
        self.key = key
        self.user_id = user_id
        self.projects = projects

    # Return a UNIX timestamp from an ActiveCollab date
    def format_date(self, date):
        if date is None:
            return
        d = datetime.datetime.fromtimestamp(time.mktime(time.strptime(
            date, "%Y-%m-%d")))
        timestamp = int(time.mktime(d.timetuple()))
        return timestamp

    # Return a priority of L, M, or H based on AC's priority index of -2 to 2
    def format_priority(self, priority):
        priority = str(priority)
        priority_map = {'-2': 'L', '-1': 'L', '0': 'M', '1': 'H', '2': 'H'}
        return priority_map[priority]

    def find_issues(self, user_id=None, project_id=None, project_name=None):
        """
        Approach:

        1. Get user ID from .bugwarriorrc file
        2. Get list of tickets from /user-tasks for a given project
        3. For each ticket/task returned from #2, get ticket/task info and
           check if logged-in user is primary (look at `is_owner` and
           `user_id`)
        """

        user_tasks_data = self.call_api(
            "/projects/" + str(project_id) + "/user-tasks")
        global task_count
        assigned_tasks = []

        try:
            for key, task in enumerate(user_tasks_data):
                task_count += 1
                assigned_task = dict()
                if task[u'type'] == 'Ticket':
                    # Load Ticket data
                    # @todo Implement threading here.
                    ticket_data = self.call_api(
                        "/projects/" + str(task[u'project_id']) +
                        "/tickets/" + str(task[u'ticket_id']))
                    assignees = ticket_data[u'assignees']

                    for k, v in enumerate(assignees):
                        if ((v[u'is_owner'] is True)
                                and (v[u'user_id'] == int(self.user_id))):
                            assigned_task['permalink'] = \
                                ticket_data[u'permalink']
                            assigned_task['ticket_id'] = \
                                ticket_data[u'ticket_id']
                            assigned_task['project_id'] = \
                                ticket_data[u'project_id']
                            assigned_task['project'] = project_name
                            assigned_task['description'] = ticket_data[u'name']
                            assigned_task['type'] = "ticket"
                            assigned_task['created_on'] = \
                                ticket_data[u'created_on']
                            assigned_task['created_by_id'] = \
                                ticket_data[u'created_by_id']
                            if 'priority' in ticket_data:
                                assigned_task['priority'] = \
                                    self.format_priority(
                                        ticket_data[u'priority'])
                            else:
                                assigned_task['priority'] = \
                                    self.default_priority
                            if ticket_data[u'due_on'] is not None:
                                assigned_task['due'] = self.format_date(
                                    ticket_data[u'due_on'])

                elif task[u'type'] == 'Task':
                    # Load Task data
                    assigned_task['permalink'] = task[u'permalink']
                    assigned_task['project'] = project_name
                    assigned_task['description'] = task[u'body']
                    assigned_task['project_id'] = task[u'project_id']
                    assigned_task['ticket_id'] = ""
                    assigned_task['type'] = "task"
                    assigned_task['created_on'] = task[u'created_on']
                    assigned_task['created_by_id'] = task[u'created_by_id']
                    if 'priority' in task:
                        assigned_task['priority'] = self.format_priority(
                            task[u'priority'])
                    else:
                        assigned_task['priority'] = self.default_priority
                    if task[u'due_on'] is not None:
                        assigned_task['due'] = self.format_date(
                            task[u'due_on'])

                if assigned_task:
                    log.name(self.target).debug(
                        " Adding '" + assigned_task['description'] +
                        "' to task list.")
                    assigned_tasks.append(assigned_task)
        except:
            log.name(self.target).debug(
                ' No user tasks loaded for "%s".' % project_name)

        return assigned_tasks

    def call_api(self, uri, get=None):
        global api_count
        api_count += 1
        url = self.url.rstrip("/") + "?token=" + self.key + \
            "&path_info=" + uri + "&format=json"
        req = urllib2.Request(url)
        res = urllib2.urlopen(req)

        return json.loads(res.read())


class ActiveCollab2Service(IssueService):
    def __init__(self, *args, **kw):
        super(ActiveCollab2Service, self).__init__(*args, **kw)

        self.url = self.config.get(self.target, 'url').rstrip("/")
        self.key = self.config.get(self.target, 'key')
        self.user_id = self.config.get(self.target, 'user_id')

        # Make a list of projects from the config
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

    def description(self, title, project_id, ticket_id="", cls="ticket"):

        cls_markup = {
            'ticket': '#',
            'task': 'Task',
        }

        return "%s%s%s - %s" % (
            MARKUP, cls_markup[cls], str(ticket_id),
            title[:45],
        )

    def format_annotation(self, created, permalink):
        return (
            "annotation_%i" % time.mktime(created.timetuple()),
            "%s" % (permalink),
        )

    def annotations(self, issue):
        return dict([
            self.format_annotation(
                datetime.datetime.fromtimestamp(time.mktime(time.strptime(
                    issue['created_on'], "%Y-%m-%d %H:%M:%S"))),
                issue['permalink'],
            )])

    def issues(self):
        # Loop through each project
        start = time.time()
        issues = []
        projects = self.projects
        # @todo Implement threading here.
        for project in projects:
            for project_id, project_name in project.iteritems():
                log.name(self.target).debug(
                    " Getting tasks for #" + project_id +
                    " " + project_name + '"')
                issues += self.client.find_issues(
                    self.user_id, project_id, project_name)

        log.name(self.target).debug(" Found {0} total.", len(issues))
        global api_count
        log.name(self.target).debug(" {0} API calls", api_count)
        log.name(self.target).debug(
            " {0} tasks and tickets analyzed", task_count)
        log.name(self.target).debug(
            " Elapsed Time: %s" % (time.time() - start))

        formatted_issues = []

        for issue in issues:
            formatted_issue = dict(
                description=self.description(
                    issue["description"],
                    issue["project_id"],
                    issue["ticket_id"],
                    issue["type"]),
                project=self.get_project_name(issue),
                priority=issue["priority"],
                **self.annotations(issue)
            )
            if "due" in issue:
                formatted_issue["due"] = issue["due"]
            formatted_issues.append(formatted_issue)

        return formatted_issues
