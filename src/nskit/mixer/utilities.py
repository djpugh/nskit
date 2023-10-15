"""Utilities for interacting with systems etc."""
import importlib.resources
from pathlib import Path
from typing import Any


from jinja2 import BaseLoader, ChoiceLoader, Environment,  TemplateNotFound
from pydantic import GetCoreSchemaHandler, TypeAdapter, ValidationError
from pydantic_core import CoreSchema, core_schema


class Resource(str):

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: Any, handler: GetCoreSchemaHandler
    ) -> CoreSchema:
        return core_schema.no_info_after_validator_function(cls._validate_resource, handler(str))

    @classmethod
    def _validate_resource(cls, value: str):
        resource_string_example = "<package>.<module>:<resource filename>"
        if ':' not in value:
            raise ValueError(f'Value should be a resource string, looking like {resource_string_example}.')
        parts = value.split(':')
        if len(parts) != 2:
            raise ValueError(f'Value should be a resource string, looking like {resource_string_example}.')
        path, filename = parts
        # filename should be a valid filename
        if len(Path(filename).parts) != 1:
            raise ValueError(f'The part after the colon ({filename}) should be a valid filename as part of the resource string ({resource_string_example}).')
        # path should be a valid module path
        if any([u in value for u in [' ', '-', '*', '(', ')']]):
            raise ValueError(f'The part before the colon ({path}) should be a valid python module path as part of the resource string ({resource_string_example}).')
        return cls(value)

    def load(self):
        """Load the resource using importlib.resources."""
        path, filename = self.split(':')
        with importlib.resources.path(path, filename) as p:
            return p.open().read()

    @classmethod
    def validate(cls, value):
        ta = TypeAdapter(Resource)
        return ta.validate_python(value)


class _PkgResourcesTemplateLoader(BaseLoader):
    """Load jinja templates via pkg_resources."""

    @staticmethod
    def get_source(environment, template):  # noqa: U100
        """Get the source using pkg_resources."""
        try:
            result = Resource.validate(template).load(), None, lambda: True
        except ValidationError as e:
            raise TemplateNotFound


JINJA_ENVIRONMENT = Environment(loader=ChoiceLoader([_PkgResourcesTemplateLoader()]))  # nosec B701
