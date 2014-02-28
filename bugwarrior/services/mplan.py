import megaplan
from twiggy import log

from bugwarrior.config import die, get_service_password
from bugwarrior.services import IssueService, Issue


class MegaplanIssue(Issue):
    URL = 'megaplan_url'
    FOREIGN_ID = 'megaplan_id'
    TITLE = 'megaplan_title'

    UDAS = {
        TITLE: {
            'type': 'string',
            'label': 'Megaplan Title',
        },
        URL: {
            'type': 'string',
            'label': 'Megaplan URL',
        },
        FOREIGN_ID: {
            'type': 'string',
            'label': 'Megaplan Issue ID'
        }
    }
    UNIQUE_KEY = (URL, )

    def to_taskwarrior(self):
        return {
            'project': self.get_project(),
            'priority': self.get_priority(),

            self.FOREIGN_ID: self.record['Id'],
            self.URL: self.get_issue_url(),
            self.TITLE: self.get_issue_title(),
        }

    def get_project(self):
        return self.origin['project_name']

    def get_default_description(self):
        return self.build_default_description(
            title=self.get_issue_title(),
            url=self.get_issue_url(),
            number=self.get_number(),
            cls='issue',
        )

    def get_issue_url(self):
        return "https://%s/task/%d/card/" % (
            self.origin['hostname'], self.record["Id"]
        )

    def get_issue_title(self):
        parts = self.record["Name"].split("|")
        return parts[-1].strip()

    def get_issue_id(self):
        if self.record["Id"] > 1000000:
            return self.record["Id"] - 1000000
        return self.record["Id"]


class MegaplanService(IssueService):
    ISSUE_CLASS = MegaplanIssue

    def __init__(self, *args, **kw):
        super(MegaplanService, self).__init__(*args, **kw)

        self.hostname = self.config.get(self.target, 'megaplan.hostname')
        _login = self.config.get(self.target, 'megaplan.login')
        _password = self.config.get(self.target, 'megaplan.password')
        if not _password or _password.startswith("@oracle:"):
            service = "megaplan://%s@%s" % (_login, self.hostname)
            _password = get_service_password(
                service, _login, oracle=_password,
                interactive=self.config.interactive
            )

        self.client = megaplan.Client(self.hostname)
        self.client.authenticate(_login, _password)

        self.project_name = self.hostname
        if self.config.has_option(self.target, "megaplan.project_name"):
            self.project_name = self.config.get(
                self.target, "megaplan.project_name"
            )

    def get_service_metadata(self):
        return {
            'project_name': self.project_name,
            'hostname': self.hostname,
        }

    @classmethod
    def validate_config(cls, config, target):
        for k in ('megaplan.login', 'megaplan.password', 'megaplan.hostname'):
            if not config.has_option(target, k):
                die("[%s] has no '%s'" % (target, k))

        IssueService.validate_config(config, target)

    def issues(self):
        issues = self.client.get_actual_tasks()
        log.name(self.target).debug(" Found {0} total.", len(issues))

        for issue in issues:
            yield self.get_issue_for_record(issue)
