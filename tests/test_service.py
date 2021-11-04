import unittest

from bugwarrior.config.load import BugwarriorConfigParser
from bugwarrior import services

LONG_MESSAGE = """\
Some message that is over 100 characters. This message is so long it's
going to fill up your floppy disk taskwarrior backup. Actually it's not
that long.""".replace('\n', ' ')


class DumbIssue(services.Issue):
    """
    Implement the required methods but they shouldn't be called.
    """
    def get_default_description(self):
        raise NotImplementedError

    def to_taskwarrior(self):
        raise NotImplementedError


class DumbIssueService(services.IssueService):
    """
    Implement the required methods but they shouldn't be called.
    """
    def get_owner(self, issue):
        raise NotImplementedError

    def issues(self):
        raise NotImplementedError

    @classmethod
    def validate_config(cls, service_config, target):
        raise NotImplementedError


class TestIssueService(unittest.TestCase):
    def setUp(self):
        super(TestIssueService, self).setUp()
        self.config = BugwarriorConfigParser()
        self.config.add_section('general')

    def test_build_annotations_default(self):
        service = DumbIssueService(self.config, 'general', 'test')

        annotations = service.build_annotations(
            (('some_author', LONG_MESSAGE),), 'example.com')
        self.assertEqual(annotations, [
            u'@some_author - Some message that is over 100 characters. Thi...'
        ])

    def test_build_annotations_limited(self):
        self.config.set('general', 'annotation_length', '20')
        service = DumbIssueService(self.config, 'general', 'test')

        annotations = service.build_annotations(
            (('some_author', LONG_MESSAGE),), 'example.com')
        self.assertEqual(
            annotations, [u'@some_author - Some message that is...'])

    def test_build_annotations_limitless(self):
        self.config.set('general', 'annotation_length', '')
        service = DumbIssueService(self.config, 'general', 'test')

        annotations = service.build_annotations(
            (('some_author', LONG_MESSAGE),), 'example.com')
        self.assertEqual(annotations, [
            u'@some_author - {message}'.format(message=LONG_MESSAGE)])


class TestIssue(unittest.TestCase):
    def setUp(self):
        super(TestIssue, self).setUp()
        self.config = BugwarriorConfigParser()
        self.config.add_section('general')

    def makeIssue(self):
        service = DumbIssueService(self.config, 'general', 'test')
        service.ISSUE_CLASS = DumbIssue
        return service.get_issue_for_record(None)

    def test_build_default_description_default(self):
        issue = self.makeIssue()

        description = issue.build_default_description(LONG_MESSAGE)
        self.assertEqual(
            description, u'(bw)Is# - Some message that is over 100 chara')

    def test_build_default_description_limited(self):
        self.config.set('general', 'description_length', '20')
        issue = self.makeIssue()

        description = issue.build_default_description(LONG_MESSAGE)
        self.assertEqual(
            description, u'(bw)Is# - Some message that is')

    def test_build_default_description_limitless(self):
        self.config.set('general', 'description_length', '')
        issue = self.makeIssue()

        description = issue.build_default_description(LONG_MESSAGE)
        self.assertEqual(
            description, u'(bw)Is# - {message}'.format(message=LONG_MESSAGE))
