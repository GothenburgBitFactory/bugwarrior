import unittest

import pydantic

from bugwarrior.config import schema


class TestValidationErrorEnhancedMessages(unittest.TestCase):
    def _create_error(self, model_class, data):
        try:
            model_class(**data)
        except pydantic.ValidationError as exc:
            return exc
        raise AssertionError("Expected ValidationError was not raised")

    def test_missing_required_field(self):
        class Model(pydantic.BaseModel):
            model_config = pydantic.ConfigDict(extra='forbid')
            required_field: str

        error = self._create_error(Model, {})
        errors = schema.ValidationErrorEnhancedMessages(error)

        self.assertEqual(len(errors), 1)
        self.assertIn("required_field", str(errors))

    def test_extra_field_forbidden(self):
        class Model(pydantic.BaseModel):
            model_config = pydantic.ConfigDict(extra='forbid')
            allowed_field: str = "default"

        error = self._create_error(Model, {"unknown_field": "value"})
        errors = schema.ValidationErrorEnhancedMessages(error)

        self.assertEqual(len(errors), 1)
        self.assertIn("unrecognized option", str(errors))

    def test_wrong_type(self):
        class Model(pydantic.BaseModel):
            model_config = pydantic.ConfigDict(extra='forbid')
            int_field: int

        error = self._create_error(Model, {"int_field": "not_an_int"})
        errors = schema.ValidationErrorEnhancedMessages(error)

        self.assertEqual(len(errors), 1)

    def test_multiple_errors(self):
        class Model(pydantic.BaseModel):
            model_config = pydantic.ConfigDict(extra='forbid')
            field1: str
            field2: int

        error = self._create_error(Model, {"field2": "not_an_int"})
        errors = schema.ValidationErrorEnhancedMessages(error)

        self.assertEqual(len(errors), 2)

    def test_nested_model_error(self):
        class NestedModel(pydantic.BaseModel):
            nested_field: str

        class ParentModel(pydantic.BaseModel):
            model_config = pydantic.ConfigDict(extra='forbid')
            child: NestedModel

        error = self._create_error(ParentModel, {"child": {}})
        errors = schema.ValidationErrorEnhancedMessages(error)

        self.assertEqual(len(errors), 1)
