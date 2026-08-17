from unittest import mock

from bugwarrior.services import bts

SERVICE_CLASS = bts.BTSService

SERVICE_CONFIG = {'service': 'bts', 'email': 'irl@debian.org', 'packages': 'bugwarrior'}


class FakeBTSBug:
    bug_num = 810629
    package = "wnpp"
    subject = (
        "ITP: bugwarrior -- Pull tickets from github, "
        "bitbucket, bugzilla, jira, trac, and others into "
        "taskwarrior"
    )
    severity = "wishlist"
    source = ""
    forwarded = ""
    pending = "pending"


class FakeBTSLib:
    def get_bugs(self, *args, **kwargs):
        return [810629]

    def get_status(self, bug_num):
        if bug_num == [810629]:
            return [FakeBTSBug]


class TestBTSService:
    def test_to_taskwarrior(self, service):
        issue = service.get_issue_for_record(service._record_for_bug(FakeBTSBug))

        expected_output = {
            'priority': issue.PRIORITY_MAP[FakeBTSBug.severity],
            'annotations': [],
            'btsurl': "https://bugs.debian.org/" + str(FakeBTSBug.bug_num),
            'btssubject': FakeBTSBug.subject,
            'btsnumber': FakeBTSBug.bug_num,
            'btspackage': FakeBTSBug.package,
            'btssource': FakeBTSBug.source,
            'btsforwarded': FakeBTSBug.forwarded,
            'btsstatus': FakeBTSBug.pending,
        }
        actual_output = issue.to_taskwarrior().to_taskwarrior_data()

        assert actual_output == expected_output

    def test_issues(self, service):
        with mock.patch('bugwarrior.services.bts.debianbts', FakeBTSLib()):
            task = next(service.issues())

        expected = {
            'annotations': [],
            'btsnumber': 810629,
            'btsforwarded': '',
            'btspackage': 'wnpp',
            'btssubject': (
                'ITP: bugwarrior -- Pull tickets from github, '
                'bitbucket, bugzilla, jira, trac, and others into '
                'taskwarrior'
            ),
            'btsurl': 'https://bugs.debian.org/810629',
            'btssource': '',
            'description': (
                '(bw)Is#810629 - ITP: bugwarrior -- Pull tickets fro .. '
                'https://bugs.debian.org/810629'
            ),
            'priority': 'L',
            'btsstatus': 'pending',
        }

        assert task.to_taskwarrior_data() == expected
