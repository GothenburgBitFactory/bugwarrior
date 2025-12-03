import unittest

import pydantic

from bugwarrior.config import schema


class TestServiceConfig(unittest.TestCase):
    def test_defaults(self):
        config = schema.ServiceConfig()
        self.assertEqual(config.only_if_assigned, '')
        self.assertFalse(config.also_unassigned)
        self.assertEqual(config.default_priority, 'M')
        self.assertEqual(config.add_tags, [])
        self.assertEqual(config.templates, {})

    def test_add_tags_from_string(self):
        config = schema.ServiceConfig(add_tags='tag1, tag2')
        self.assertEqual(config.add_tags, ['tag1', 'tag2'])

    def test_invalid_priority(self):
        with self.assertRaises(pydantic.ValidationError):
            schema.ServiceConfig(default_priority='X')

    def test_valid_priorities(self):
        for priority in ['', 'L', 'M', 'H']:
            config = schema.ServiceConfig(default_priority=priority)
            self.assertEqual(config.default_priority, priority)

    def test_template_field(self):
        config = schema.ServiceConfig(project_template='myproject')
        self.assertEqual(config.templates, {'project': 'myproject'})

    def test_multiple_templates(self):
        config = schema.ServiceConfig(project_template='proj', priority_template='H')
        self.assertEqual(config.templates['project'], 'proj')
        self.assertEqual(config.templates['priority'], 'H')
