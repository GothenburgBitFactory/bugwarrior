import copy
from types import SimpleNamespace

import taskw.task

from bugwarrior import db
from bugwarrior.collect import CollectedIssue

from .base import ConfigTest


class TestMergeAnnotations:
    def test_merges_local_and_remote_annotations(self):
        local = {'annotations': ['existing']}
        remote = {'annotations': ['new', 'new']}

        assert db.merge_annotations(local, remote) == ['existing', 'new', 'new']

    def test_skips_normalized_matches(self):
        local = {'annotations': ['testing']}
        remote = {'annotations': ['\n  testing  \n']}

        assert db.merge_annotations(local, remote) == ['testing']

    def test_adds_annotation_that_extends_existing_one(self):
        local = {'annotations': ['testing']}
        remote = {'annotations': ['testing with more detail']}

        assert db.merge_annotations(local, remote) == [
            'testing',
            'testing with more detail',
        ]

    def test_handles_missing_annotations(self):
        assert db.merge_annotations({}, {}) == []
        assert db.merge_annotations({}, {'annotations': ['new']}) == ['new']


class TestMergeTags:
    def test_merges_and_sorts_unique_tags(self):
        main_conf = SimpleNamespace(replace_tags=False, static_tags=[])
        local = {'tags': ['existing', 'shared']}
        remote = {'tags': ['new', 'shared']}

        assert db.merge_tags(main_conf, local, remote) == ['existing', 'new', 'shared']

    def test_replaces_non_static_local_tags_when_configured(self):
        main_conf = SimpleNamespace(replace_tags=True, static_tags=['keep'])
        local = {'tags': ['drop', 'keep']}
        remote = {'tags': ['new']}

        assert db.merge_tags(main_conf, local, remote) == ['keep', 'new']

    def test_handles_missing_tags(self):
        main_conf = SimpleNamespace(replace_tags=False, static_tags=[])

        assert db.merge_tags(main_conf, {}, {}) == []
        assert db.merge_tags(main_conf, {}, {'tags': ['new']}) == ['new']


class TestSynchronize(ConfigTest):
    def setUp(self):
        super().setUp()
        self.config = {
            'general': {
                'targets': ['my_service'],
                'taskrc': self.taskrc,
                'static_fields': ['project', 'priority'],
            },
            'my_service': {
                'service': 'github',
                'login': 'ralphbean',
                'username': 'ralphbean',
                'token': 'abc123',
            },
        }
        self.bwconfig = self.validate()
        self.tw = taskw.TaskWarrior(self.taskrc)

    def synchronize(self, issues_data):

        issue_generator = [
            CollectedIssue(
                task_data=copy.deepcopy(issue_data),
                target="my_service",
                identifier="abcd",
            )
            for issue_data in issues_data
        ]
        db.synchronize(iter(issue_generator), self.bwconfig)

    def remove_non_deterministic_keys(self, tasks):
        for status in ['pending', 'completed']:
            for task in tasks[status]:
                del task['modified']
                del task['entry']
                del task['uuid']
                task['tags'] = sorted(task['tags'])

        return tasks

    def get_tasks(self):

        return self.remove_non_deterministic_keys(self.tw.load_tasks())

    def test_synchronize(self):

        self.assertEqual(self.tw.load_tasks(), {'completed': [], 'pending': []})

        issue = {
            'description': 'Blah blah blah. ☃',
            'project': 'sample_project',
            'githubtype': 'issue',
            'githuburl': 'https://example.com',
            'priority': 'M',
            'tags': ['foo'],
        }
        duplicate_issue = copy.deepcopy(issue)
        duplicate_issue['tags'] = ['bar']

        # TEST NEW ISSUE AND EXISTING ISSUE.
        for _ in range(2):
            # Use an issue generator with two copies of the same issue.
            # These should be de-duplicated in db.synchronize before
            # writing out to taskwarrior.
            # https://github.com/ralphbean/bugwarrior/issues/601
            self.synchronize([issue, duplicate_issue])

            self.assertEqual(
                self.get_tasks(),
                {
                    'completed': [],
                    'pending': [
                        {
                            'project': 'sample_project',
                            'priority': 'M',
                            'status': 'pending',
                            'description': 'Blah blah blah. ☃',
                            'githuburl': 'https://example.com',
                            'githubtype': 'issue',
                            'id': 1,
                            'tags': ['bar', 'foo'],
                            'urgency': 5.8,
                        }
                    ],
                },
            )

        # TEST CHANGED ISSUE.
        issue['description'] = 'Yada yada yada.'

        # Change static field
        issue['project'] = 'other_project'
        self.synchronize([issue])

        self.assertEqual(
            self.get_tasks(),
            {
                'completed': [],
                'pending': [
                    {
                        'priority': 'M',
                        'project': 'sample_project',
                        'status': 'pending',
                        'description': 'Yada yada yada.',
                        'githuburl': 'https://example.com',
                        'githubtype': 'issue',
                        'id': 1,
                        'tags': ['bar', 'foo'],
                        'urgency': 5.8,
                    }
                ],
            },
        )

        # TEST CLOSED ISSUE.
        self.synchronize([])

        completed_tasks = self.tw.load_tasks()

        tasks = self.remove_non_deterministic_keys(copy.deepcopy(completed_tasks))
        del tasks['completed'][0]['end']
        self.assertEqual(
            tasks,
            {
                'completed': [
                    {
                        'project': 'sample_project',
                        'description': 'Yada yada yada.',
                        'githubtype': 'issue',
                        'githuburl': 'https://example.com',
                        'id': 0,
                        'priority': 'M',
                        'status': 'completed',
                        'tags': ['bar', 'foo'],
                        'urgency': 5.8,
                    }
                ],
                'pending': [],
            },
        )

        # TEST REOPENED ISSUE
        self.synchronize([issue])

        tasks = self.tw.load_tasks()
        self.assertEqual(
            completed_tasks['completed'][0]['uuid'], tasks['pending'][0]['uuid']
        )

        tasks = self.remove_non_deterministic_keys(tasks)
        self.assertEqual(
            tasks,
            {
                'completed': [],
                'pending': [
                    {
                        'priority': 'M',
                        'project': 'sample_project',
                        'status': 'pending',
                        'description': 'Yada yada yada.',
                        'githuburl': 'https://example.com',
                        'githubtype': 'issue',
                        'id': 1,
                        'tags': ['bar', 'foo'],
                        'urgency': 5.8,
                    }
                ],
            },
        )


class TestUDAs(ConfigTest):
    def test_udas(self):
        self.config = {
            'general': {'targets': ['my_service']},
            'my_service': {
                'service': 'github',
                'login': 'ralphbean',
                'username': 'ralphbean',
                'token': 'abc123',
            },
        }

        conf = self.validate()
        udas = sorted(list(db.get_defined_udas_as_strings(conf)))
        self.assertEqual(
            udas,
            [
                'uda.githubbody.label=Github Body',
                'uda.githubbody.type=string',
                'uda.githubclosedon.label=GitHub Closed',
                'uda.githubclosedon.type=date',
                'uda.githubcreatedon.label=Github Created',
                'uda.githubcreatedon.type=date',
                'uda.githubdraft.label=GitHub Draft',
                'uda.githubdraft.type=numeric',
                'uda.githubmilestone.label=Github Milestone',
                'uda.githubmilestone.type=string',
                'uda.githubnamespace.label=Github Namespace',
                'uda.githubnamespace.type=string',
                'uda.githubnumber.label=Github Issue/PR #',
                'uda.githubnumber.type=numeric',
                'uda.githubrepo.label=Github Repo Slug',
                'uda.githubrepo.type=string',
                'uda.githubstate.label=GitHub State',
                'uda.githubstate.type=string',
                'uda.githubtitle.label=Github Title',
                'uda.githubtitle.type=string',
                'uda.githubtype.label=Github Type',
                'uda.githubtype.type=string',
                'uda.githubupdatedat.label=Github Updated',
                'uda.githubupdatedat.type=date',
                'uda.githuburl.label=Github URL',
                'uda.githuburl.type=string',
                'uda.githubuser.label=Github User',
                'uda.githubuser.type=string',
            ],
        )
