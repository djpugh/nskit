from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Union

from jinja2 import Template as JinjaTemplate
from pydantic import Field, GetCoreSchemaHandler
from pydantic_core import CoreSchema, core_schema


from nskit.common.configuration import BaseConfiguration


class TemplateStr(str):

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: Any, handler: GetCoreSchemaHandler
    ) -> CoreSchema:
        return core_schema.no_info_after_validator_function(cls._validate_resource, handler(str))

    @classmethod
    def _validate_resource(cls, value: str):
        resource_string_example = "<package>.<module>:<resource filename>"
        if ('{{' in value and '}}' in value) or ('{%' in value and '%}' in value):
            return cls(value)
        else:
            raise ValueError(f'Template str needs jinja syntax.')

    def __call__(self, context: Dict[str, Union[str, int]] = {}):
        """Render the template."""
        return JinjaTemplate(self).render(context)


class FileSystemObject(ABC, BaseConfiguration):
    """Abstract pydantic model that acts as the base for filesystem objects."""

    id_: Optional[Union[int, str]] = Field(None, description="An Id to refer to the object when e.g. the name is a template string or callable")
    name: Optional[Union[TemplateStr, str, Callable]] = Field(..., validate_default=True, description='The name of the filesystem object, can be  a string, TemplateStr or callable (which returns a string)')

    def render_name(self, context: Dict[str, Union[str, int]] = {}):
        if not isinstance(context, dict):
            raise TypeError(f'Context must be a dict, not {type(context)}')
        if isinstance(self.name, TemplateStr) or not isinstance(self.name, str):
            # Either a callable or TemplateStr (which is a callable)
            rendered_name = self.name(context)
        else:
            rendered_name = self.name
        return rendered_name

    def _repr(self, context=None, **kwargs):
        if isinstance(self.name, TemplateStr):
            name_value = self.name
            name = 'name <TemplateStr>'
        elif isinstance(self.name, str):
            name = 'name'
            name_value = self.name
        else:
            name_value = '<callable>'
            name = 'name'
        rendered_name = name_value
        if context:
            rendered_name = self.render_name(context)
        if self.id_:
            id_ = f'id: {self.id_}, '
        else:
            id_ = ''
        return f'{rendered_name} = {self.__class__.__name__}({id_}{name}: {name_value})'

    def __repr__(self):
        return self._repr()

    def get_path(self, base_path: Path, context: Dict[str, Union[str, int]], override_path: Optional[Path] = None):
        """Get the object path. Can be overriden with the override_path (relative to the base path)."""
        if override_path:
            path = Path(base_path)/Path(override_path)
        else:
            path = Path(base_path) / self.render_name(context)
        return path

    @abstractmethod
    def write(self, base_path: Path, context: Dict[str, Any], override_path: Optional[Path] = None):
        """Write the object to the appropriate path within the ``base_path``."""
        raise NotImplementedError()

    @abstractmethod
    def dryrun(self, base_path: Path, context: Dict[str, Any], override_path: Optional[Path] = None):
        """Preview the file contents using the context."""
        raise NotImplementedError()

    @abstractmethod
    def validate(self, base_path: Path, context: Dict[str, Any], override_path: Optional[Path] = None):
        """Validate the output against expected."""
        raise NotImplementedError()
