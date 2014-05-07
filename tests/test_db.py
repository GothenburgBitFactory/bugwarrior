import unittest2

import taskw.task
from bugwarrior.db import merge_left


class DBTest(unittest2.TestCase):
    def setUp(self):
        self.issue_dict = {'annotations': ['testing']}

    def test_merge_left_with_dict(self):
        task = {}
        merge_left('annotations', task, self.issue_dict)
        self.assertEquals(task, self.issue_dict)

    def test_merge_left_with_taskw(self):
        task = taskw.task.Task({})
        merge_left('annotations', task, self.issue_dict)
        self.assertEquals(task, self.issue_dict)
