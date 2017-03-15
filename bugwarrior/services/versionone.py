from v1pysdk import V1Meta
from v1pysdk.none_deref import NoneDeref
from six.moves.urllib import parse

from bugwarrior.services import IssueService, Issue, LOCAL_TIMEZONE
from bugwarrior.config import die


class VersionOneIssue(Issue):
    TASK_NAME = 'versiononetaskname'
    TASK_DESCRIPTION = 'versiononetaskdescrption'
    TASK_ESTIMATE = 'versiononetaskestimate'
    TASK_DETAIL_ESTIMATE = 'versiononetaskdetailestimate'
    TASK_TO_DO = 'versiononetasktodo'
    TASK_REFERENCE = 'versiononetaskreference'
    TASK_URL = 'versiononetaskurl'
    TASK_OID = 'versiononetaskoid'

    STORY_NAME = 'versiononestoryname'
    STORY_DESCRIPTION = 'versiononestorydescription'
    STORY_ESTIMATE = 'versiononestoryestimate'
    STORY_DETAIL_ESTIMATE = 'versiononestorydetailestimate'
    STORY_URL = 'versiononestoryurl'
    STORY_NUMBER = 'versiononestorynumber'
    STORY_OID = 'versiononestoryoid'

    TIMEBOX_BEGIN_DATE = 'versiononetimeboxbegindate'
    TIMEBOX_END_DATE = 'versiononetimeboxenddate'
    TIMEBOX_NAME = 'versiononetimeboxname'

    UDAS = {
        TASK_NAME: {
            'type': 'string',
            'label': 'VersionOne Task Name'
        },
        TASK_DESCRIPTION: {
            'type': 'string',
            'label': 'VersionOne Task Description'
        },
        TASK_ESTIMATE: {
            'type': 'string',
            'label': 'VersionOne Task Estimate'
        },
        TASK_DETAIL_ESTIMATE: {
            'type': 'string',
            'label': 'VersionOne Task Detail Estimate',
        },
        TASK_TO_DO: {
            'type': 'string',
            'label': 'VersionOne Task To Do'
        },
        TASK_REFERENCE: {
            'type': 'string',
            'label': 'VersionOne Task Reference'
        },
        TASK_URL: {
            'type': 'string',
            'label': 'VersionOne Task URL'
        },
        TASK_OID: {
            'type': 'string',
            'label': 'VersionOne Task Object ID'
        },
        STORY_NAME: {
            'type': 'string',
            'label': 'VersionOne Story Name'
        },
        STORY_DESCRIPTION: {
            'type': 'string',
            'label': 'VersionOne Story Description'
        },
        STORY_ESTIMATE: {
            'type': 'string',
            'label': 'VersionOne Story Estimate'
        },
        STORY_DETAIL_ESTIMATE: {
            'type': 'string',
            'label': 'VersionOne Story Detail Estimate'
        },
        STORY_URL: {
            'type': 'string',
            'label': 'VersionOne Story URL'
        },
        STORY_NUMBER: {
            'type': 'string',
            'label': 'VersionOne Story Number'
        },
        STORY_OID: {
            'type': 'string',
            'label': 'VersionOne Story Object ID'
        },
        TIMEBOX_BEGIN_DATE: {
            'type': 'string',
            'label': 'VersionOne Timebox Begin Date'
        },
        TIMEBOX_END_DATE: {
            'type': 'string',
            'label': 'VersionOne Timebox End Date'
        },
        TIMEBOX_NAME: {
            'type': 'string',
            'label': 'VersionOne Timebox Name'
        }
    }

    UNIQUE_KEY = (TASK_URL, )

    def to_taskwarrior(self):
        return {
            'project': self.extra['project'],
            'priority': self.origin['default_priority'],
            'due': self.parse_date(
                self.record['timebox']['EndDate'],
                self.origin['timezone']
            ),

            self.TASK_NAME: self.record['task']['Name'],
            self.TASK_DESCRIPTION: self.record['task']['Description'],
            self.TASK_ESTIMATE: self.record['task']['Estimate'],
            self.TASK_DETAIL_ESTIMATE: self.record['task']['DetailEstimate'],
            self.TASK_TO_DO: self.record['task']['ToDo'],
            self.TASK_REFERENCE: self.record['task']['Reference'],
            self.TASK_URL: self.record['task']['url'],
            self.TASK_OID: self.record['task']['idref'],

            self.STORY_NAME: self.record['story']['Name'],
            self.STORY_DESCRIPTION: self.record['story']['Description'],
            self.STORY_ESTIMATE: self.record['story']['Estimate'],
            self.STORY_DETAIL_ESTIMATE: self.record['story']['DetailEstimate'],
            self.STORY_URL: self.record['story']['url'],
            self.STORY_OID: self.record['story']['idref'],
            self.STORY_NUMBER: self.record['story']['Number'],

            self.TIMEBOX_BEGIN_DATE: self.record['timebox']['BeginDate'],
            self.TIMEBOX_END_DATE: self.record['timebox']['EndDate'],
            self.TIMEBOX_NAME: self.record['timebox']['Name'],
        }

    def get_default_description(self):
        return self.build_default_description(
            title=': '.join([
                self.record['story']['Name'],
                self.record['task']['Name'],
            ]),
            url=self.record['task']['url'],
            number=self.record['story']['Number'],
            cls='task',
        )


class VersionOneService(IssueService):
    ISSUE_CLASS = VersionOneIssue
    CONFIG_PREFIX = 'versionone'

    TASK_COLLECT_DATA = (
        'Name',
        'Description',
        'Estimate',
        'DetailEstimate',
        'ToDo',
        'Reference',
        'url',
        'idref',
    )
    STORY_COLLECT_DATA = (
        'Name',
        'Description',
        'Estimate',
        'DetailEstimate',
        'Number',
        'url',
        'idref',
    )
    TIMEBOX_COLLECT_DATA = (
        'BeginDate',
        'EndDate',
        'Name',
    )

    def __init__(self, *args, **kw):
        super(VersionOneService, self).__init__(*args, **kw)

        parsed_address = parse.urlparse(
            self.config.get('base_uri')
        )
        self.address = parsed_address.netloc
        self.instance = parsed_address.path.strip('/')
        self.username = self.config.get('username')
        self.password = self.get_password('password', self.username)

        self.timezone = self.config.get('timezone', default=LOCAL_TIMEZONE)
        self.project = self.config.get('project_name', default='')
        self.timebox_name = self.config.get('timebox_name')

    @staticmethod
    def get_keyring_service(service_config):
        parsed_address = parse.urlparse(service_config.get('base_uri'))
        username = service_config.get('username')
        return "versionone://%s@%s%s" % (
            username,
            parsed_address.netloc,
            parsed_address.path
        )

    def get_service_metadata(self):
        return {
            'timezone': self.timezone
        }

    @classmethod
    def validate_config(cls, service_config, target):
        options = (
            'base_uri',
            'username',
        )
        for option in options:
            if option not in service_config:
                die("[%s] has no 'versionone.%s'" % (target, option))

        IssueService.validate_config(service_config, target)

    def get_meta(self):
        if not hasattr(self, '_meta'):
            self._meta = V1Meta(
                address=self.address,
                instance=self.instance,
                username=self.username,
                password=self.password
            )
        return self._meta

    def get_assignments(self, username):
        meta = self.get_meta()
        where = {
            'IsClosed': False,
            'IsCompleted': False,
            'IsDead': False,
            'IsDeleted': False,
            'IsInactive': False,
        }
        if self.timebox_name:
            where['Parent.Timebox.Name'] = self.timebox_name

        tasks = meta.Task.select(
            'Name',
            'Parent',
            'Description',
            'Estimate',
            'DetailEstimate',
            'ToDo',
            'Reference',
        ).filter(
            "Owners.Username='{username}'".format(username=self.username)
        ).where(**where)
        return tasks

    def issues(self):
        for issue in self.get_assignments(self.username):
            issue_data = {
                'task': {},
                'story': {},
                'timebox': {},
            }
            field_maps = (
                ('task', issue, self.TASK_COLLECT_DATA, ),
                ('story', issue.Parent, self.STORY_COLLECT_DATA, ),
                ('timebox', issue.Parent.Timebox, self.TIMEBOX_COLLECT_DATA, ),
            )
            for key, source, columns in field_maps:
                for column in columns:
                    value = getattr(source, column, None)
                    # NoneDeref is a special kind of None used by the v1 client
                    if isinstance(value, NoneDeref):
                        value = None
                    issue_data[key][column] = value

            extras = {
                'project': self.project
            }

            yield self.get_issue_for_record(
                issue_data,
                extras
            )
