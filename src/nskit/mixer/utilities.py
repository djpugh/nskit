"""Utilities for interacting with systems etc."""
import os
from pathlib import Path
import sys
from typing import Any

if sys.version_info.major <= 3 and sys.version_info.minor < 9:
    from importlib_resources import files
else:
    from importlib.resources import files

from jinja2 import BaseLoader, ChoiceLoader, Environment, TemplateNotFound
from pydantic import GetCoreSchemaHandler, TypeAdapter, ValidationError
from pydantic_core import core_schema, CoreSchema

from nskit.common.extensions import ExtensionsEnum


class Resource(str):
    """A type for a package resource uri."""

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: Any, handler: GetCoreSchemaHandler  # noqa: U100
    ) -> CoreSchema:
        """Get the schema."""
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
        invalid_path = [u in path for u in [' ', '-', '*', '(', ')']]
        if any(invalid_path):
            raise ValueError(f'The part before the colon ({path}) should be a valid python module path as part of the resource string ({resource_string_example}).')
        return cls(value)

    def load(self):
        """Load the resource using importlib.resources."""
        path, filename = self.split(':')
        with files(path).joinpath(filename) as p:
            return p.open().read()

    @classmethod
    def validate(cls, value):
        """Validate the input."""
        ta = TypeAdapter(Resource)
        return ta.validate_python(value)


class _PkgResourcesTemplateLoader(BaseLoader):
    """Load jinja templates via imporlib.resources."""

    @staticmethod
    def get_source(environment, template):  # noqa: U100
        """Get the source using imporlib.resources."""
        try:
            Resource.validate(template)
        except ValidationError as e:
            raise TemplateNotFound(template, *e.args)
        resource = Resource(template)
        try:
            source = resource.load()
        except FileNotFoundError:
            raise TemplateNotFound(template)
        return source, None, lambda: True


class _EnvironmentFactory():
    """Jinja2 Environment Factory to allow for extension/customisation."""

    def __init__(self):
        """Initialise the factory."""
        self._environment = None

    @property
    def environment(self) -> Environment:
        """Handle caching the environment object so it is lazily initialised."""
        if self._environment is None:
            self._environment = self.get_environment()
            self.add_extensions(self._environment)
        return self._environment

    def add_extensions(self, environment: Environment):
        """Add Extensions to the environment object."""
        NskitMixerExtensionOptions = ExtensionsEnum.from_entrypoint('NskitMixerExtensionOptions', 'nskit.mixer.environment.extensions')
        # Assuming no risk of extension clash
        extensions = []
        for ext in NskitMixerExtensionOptions:
            extensions += ext.extension()
        for extension in list(set(extensions)):
            environment.add_extension(extension)

    def get_environment(self) -> Environment:
        """Get the environment object based on the env var."""
        selected_method = os.environ.get('NSKIT_MIXER_ENVIRONMENT_FACTORY', None)
        if selected_method is None or selected_method.lower() == 'default':
            # This is our simple implementation
            selected_method = 'default'
        # We need to validate against the options
        NskitMixerEnvironmentOptions = ExtensionsEnum.from_entrypoint('NskitMixerEnvironmentOptions', 'nskit.mixer.environment.factory')
        if sys.version_info.major <= 3 and sys.version_info.minor < 12:
            if selected_method not in NskitMixerEnvironmentOptions.__members__.keys():
                raise ValueError(f'NSKIT_MIXER_ENVIRONMENT_FACTORY value {selected_method} not installed - available options are {list(NskitMixerEnvironmentOptions)}')
        else:
            if selected_method not in NskitMixerEnvironmentOptions:
                raise ValueError(f'NSKIT_MIXER_ENVIRONMENT_FACTORY value {selected_method} not installed - available options are {list(NskitMixerEnvironmentOptions)}')
        return NskitMixerEnvironmentOptions(selected_method).extension()

    @staticmethod
    def default_environment():
        """Get the default environment object."""
        return Environment(loader=ChoiceLoader([_PkgResourcesTemplateLoader()]))  # nosec B701


JINJA_ENVIRONMENT_FACTORY = _EnvironmentFactory()
