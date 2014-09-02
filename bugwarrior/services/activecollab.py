import re

import pypandoc
from twiggy import log
from pyac.library import activeCollab
from bugwarrior.services import IssueService, Issue
from bugwarrior.config import die


class ActiveCollabClient(object):
    def __init__(self, url, key, user_id):
        self.url = url
        self.key = key
        self.user_id = int(user_id)
        self.activecollabtivecollab = activeCollab(
            key=key,
            url=url,
            user_id=user_id
        )


class ActiveCollabIssue(Issue):
    BODY = 'acbody'
    NAME = 'acname'
    PERMALINK = 'acpermalink'
    TASK_ID = 'actaskid'
    FOREIGN_ID = 'acid'
    PROJECT_ID = 'acprojectid'
    PROJECT_NAME = 'acprojectname'
    TYPE = 'actype'
    CREATED_ON = 'accreatedon'
    CREATED_BY_NAME = 'accreatedbyname'
    ESTIMATED_TIME = 'acestimatedtime'
    TRACKED_TIME = 'actrackedtime'
    MILESTONE = 'acmilestone'
    LABEL = 'aclabel'

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
            'type': 'numeric',
            'label': 'ActiveCollab Task ID'
        },
        FOREIGN_ID: {
            'type': 'numeric',
            'label': 'ActiveCollab ID',
        },
        PROJECT_ID: {
            'type': 'numeric',
            'label': 'ActiveCollab Project ID'
        },
        PROJECT_NAME: {
            'type': 'string',
            'label': 'ActiveCollab Project Name'
        },
        TYPE: {
            'type': 'string',
            'label': 'ActiveCollab Task Type'
        },
        CREATED_ON: {
            'type': 'date',
            'label': 'ActiveCollab Created On'
        },
        CREATED_BY_NAME: {
            'type': 'string',
            'label': 'ActiveCollab Created By'
        },
        ESTIMATED_TIME: {
            'type': 'numeric',
            'label': 'ActiveCollab Estimated Time'
        },
        TRACKED_TIME: {
            'type': 'numeric',
            'label': 'ActiveCollab Tracked Time'
        },
        MILESTONE: {
            'type': 'string',
            'label': 'ActiveCollab Milestone'
        },
        LABEL: {
            'type': 'string',
            'label': 'ActiveCollab Label'
        }
    }
    UNIQUE_KEY = (FOREIGN_ID, )

    def to_taskwarrior(self):
        record = {
            'project': re.sub(r'\W+', '-', self.record['project']).lower(),
            'priority': self.get_priority(),
            'annotations': self.extra.get('annotations', []),
            self.NAME: self.record.get('name', ''),
            self.BODY: pypandoc.convert(self.record.get('body'),
                                        'md', format='html').rstrip(),
            self.PERMALINK: self.record['permalink'],
            self.TASK_ID: int(self.record.get('task_id')),
            self.PROJECT_NAME: self.record['project'],
            self.PROJECT_ID: int(self.record['project_id']),
            self.FOREIGN_ID: int(self.record['id']),
            self.TYPE: self.record.get('type', 'subtask').lower(),
            self.CREATED_BY_NAME: self.record['created_by_name'],
            self.MILESTONE: self.record['milestone'],
            self.ESTIMATED_TIME: self.record.get('estimated_time', 0),
            self.TRACKED_TIME: self.record.get('tracked_time', 0),
            self.LABEL: self.record.get('label'),
        }

        if self.TYPE == 'subtask':
            # Store the parent task ID for subtasks
            record['actaskid'] = int(self.record['task_id'])

        if isinstance(self.record.get('due_on'), dict):
            record['due'] = self.parse_date(
                self.record.get('due_on')['formatted_date']
            )

        if isinstance(self.record.get('created_on'), dict):
            record[self.CREATED_ON] = self.parse_date(
                self.record.get('created_on')['formatted_date']
            )
        return record

    def get_annotations(self):
        return self.extra.get('annotations', [])

    def get_priority(self):
        value = self.record.get('priority')
        if value > 0:
            return 'H'
        elif value < 0:
            return 'L'
        else:
            return 'M'

    def get_default_description(self):
        return self.build_default_description(
            title=(
                self.record.get('name')
                if self.record.get('name')
                else self.record.get('body')
            ),
            url=self.get_processed_url(self.record['permalink']),
            number=self.record['id'],
            cls=self.record.get('type', 'subtask').lower(),
        )


class ActiveCollabService(IssueService):
    ISSUE_CLASS = ActiveCollabIssue
    CONFIG_PREFIX = 'activecollab'

    def __init__(self, *args, **kw):
        super(ActiveCollabService, self).__init__(*args, **kw)

        self.url = self.config_get('url').rstrip('/')
        self.key = self.config_get('key')
        self.user_id = int(self.config_get('user_id'))
        self.client = ActiveCollabClient(
            self.url, self.key, self.user_id
        )
        self.activecollab = activeCollab(url=self.url, key=self.key,
                                         user_id=self.user_id)

    @classmethod
    def validate_config(cls, config, target):
        for k in (
            'activecollab.url', 'activecollab.key', 'activecollab.user_id'
        ):
            if not config.has_option(target, k):
                die("[%s] has no '%s'" % (target, k))

        IssueService.validate_config(config, target)

    def _comments(self, issue):
        comments = self.activecollab.get_comments(
            issue['project_id'],
            issue['task_id']
        )
        comments_formatted = []
        if comments is not None:
            for comment in comments:
                comments_formatted.append(
                    dict(user=comment['created_by']['display_name'],
                         body=comment['body']))
        return comments_formatted

    def get_owner(self, issue):
        if issue['assignee_id']:
            return issue['assignee_id']

    def annotations(self, issue, issue_obj):
        if 'type' not in issue:
            # Subtask
            return []
        comments = self._comments(issue)
        if comments is None:
            return []

        return self.build_annotations(
            ((
                c['user'],
                pypandoc.convert(c['body'], 'md', format='html').rstrip()
            ) for c in comments),
            issue_obj.get_processed_url(issue_obj.record['permalink']),
        )

    def issues(self):
        data = self.activecollab.get_my_tasks()
        label_data = self.activecollab.get_assignment_labels()
        labels = dict()
        for item in label_data:
            labels[item['id']] = re.sub(r'\W+', '_', item['name'])
        task_count = 0
        issues = []
        for key, record in data.iteritems():
            for task_id, task in record['assignments'].iteritems():
                task_count = task_count + 1
                # Add tasks
                if task['assignee_id'] == self.user_id:
                    task['label'] = labels.get(task['label_id'])
                    issues.append(task)
                if 'subtasks' in task:
                    for subtask_id, subtask in task['subtasks'].iteritems():
                        # Add subtasks
                        task_count = task_count + 1
                        if subtask['assignee_id'] is self.user_id:
                            # Add some data from the parent task
                            subtask['label'] = labels.get(subtask['label_id'])
                            subtask['project_id'] = task['project_id']
                            subtask['project'] = task['project']
                            subtask['task_id'] = task['task_id']
                            subtask['milestone'] = task['milestone']
                            issues.append(subtask)
        log.name(self.target).debug(" Found {0} total", task_count)
        log.name(self.target).debug(" Pruned down to {0}", len(issues))
        for issue in issues:
            issue_obj = self.get_issue_for_record(issue)
            extra = {
                'annotations': self.annotations(issue, issue_obj)
            }
            issue_obj.update_extra(extra)
            yield issue_obj
