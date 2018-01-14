from builtins import next
from builtins import str
from builtins import object
import mock

from bugwarrior.services import bts

from .base import ServiceTest, AbstractServiceTest


class FakeBTSBug(object):
    bug_num = 810629
    package = "wnpp"
    subject = ("ITP: bugwarrior -- Pull tickets from github, "
               "bitbucket, bugzilla, jira, trac, and others into "
               "taskwarrior")
    severity = "wishlist"
    source = ""
    forwarded = ""
    pending = "pending"


class FakeBTSLib(object):
    def get_bugs(self, *args, **kwargs):
        return [810629]

    def get_status(self, bug_num):
        if bug_num == [810629]:
            return [FakeBTSBug]


class TestBTSService(AbstractServiceTest, ServiceTest):

    maxDiff = None

    SERVICE_CONFIG = {
        'bts.email': 'irl@debian.org',
        'bts.packages': 'bugwarrior',
    }

    def setUp(self):
        super(TestBTSService, self).setUp()
        self.service = self.get_mock_service(bts.BTSService)

    def test_to_taskwarrior(self):
        issue = self.service.get_issue_for_record(
            self.service._record_for_bug(FakeBTSBug)
        )

        expected_output = {
            'priority': issue.PRIORITY_MAP[FakeBTSBug.severity],
            'annotations': [],

            issue.URL: "https://bugs.debian.org/" + str(FakeBTSBug.bug_num),
            issue.SUBJECT: FakeBTSBug.subject,
            issue.NUMBER: FakeBTSBug.bug_num,
            issue.PACKAGE: FakeBTSBug.package,
            issue.SOURCE: FakeBTSBug.source,
            issue.FORWARDED: FakeBTSBug.forwarded,
            issue.STATUS: FakeBTSBug.pending,
        }
        actual_output = issue.to_taskwarrior()

        self.assertEqual(actual_output, expected_output)

    def test_issues(self):
        with mock.patch('bugwarrior.services.bts.debianbts', FakeBTSLib()):
            issue = next(self.service.issues())

        expected = {
            'annotations': [],
            'btsnumber': 810629,
            'btsforwarded': '',
            'btspackage': 'wnpp',
            'btssubject': ('ITP: bugwarrior -- Pull tickets from github, '
                           'bitbucket, bugzilla, jira, trac, and others into '
                           'taskwarrior'),
            'btsurl': 'https://bugs.debian.org/810629',
            'btssource': '',
            'description': (u'(bw)Is#810629 - ITP: bugwarrior -- Pull tickets'
                            u' from github, bitbucket, bugzilla, jira, trac, '
                            u'and others into taskwa .. https://bugs.debian.o'
                            u'rg/810629'),
            'priority': 'L',
            'btsstatus': 'pending',
            u'tags': []}

        self.assertEqual(issue.get_taskwarrior_record(), expected)
