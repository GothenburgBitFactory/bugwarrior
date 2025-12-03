import unittest

import pydantic

from bugwarrior.config import schema


class TestConfigList(unittest.TestCase):
    def test_simple_list(self):
        result = schema.parse_config_list('project_bar,project_baz')
        self.assertEqual(result, ['project_bar', 'project_baz'])

    def test_jinja_template(self):
        value = "work, jira, {{jirastatus|lower|replace(' ','_')}}"
        result = schema.parse_config_list(value)
        self.assertEqual(
            result, ['work', 'jira', "{{jirastatus|lower|replace(' ','_')}}"]
        )

    def test_empty_string(self):
        result = schema.parse_config_list('')
        self.assertEqual(result, [])

    def test_list_passthrough(self):
        value = ['already', 'a', 'list']
        result = schema.parse_config_list(value)
        self.assertEqual(result, value)

    def test_in_model(self):
        class Model(pydantic.BaseModel):
            items: schema.ConfigList = []

        model = Model(items='foo, bar, baz')
        self.assertEqual(model.items, ['foo', 'bar', 'baz'])
