from abc import ABC
from pathlib import Path
from typing import Callable, Dict, Optional, Union

from jinja2 import Template as JinjaTemplate
from pydantic import BaseModel, Field


from nskit.common.configuration import BaseConfiguration


class TemplateStr(BaseModel):
    """Pydantic model with a template field, that is rendered (as a string) when the object is called using a context."""

    template: str

    def __call__(self, context: Dict[str, Union[str, int]] = {}):
        """Render the template."""
        return JinjaTemplate(self.template).render(context)


class FileSystemObject(ABC, BaseConfiguration):
    """Abstract pydantic model that acts as the base for filesystem objects."""

    id_: Optional[Union[int, str]] = Field(None, description="An Id to refer to the object when e.g. the name is a template string or callable")
    name: Optional[Union[str, Callable, TemplateStr]] = Field(..., validate_default=True, description='The name of the filesystem object, can be  a string, TemplateStr or callable (which returns a string)')

    def render_name(self, context: Dict[str, Union[str, int]] = {}):
        if not isinstance(context, dict):
            raise TypeError(f'Context must be a dict, not {type(context)}')
        if not isinstance(self.name, str):
            # Either a callable or TemplateStr (which is a callable)
            rendered_name = self.name(context)
        else:
            rendered_name = self.name
        return rendered_name

    def _repr(self, context=None, **kwargs):
        if isinstance(self.name, str):
            name = self.name
            name_value = self.name
        else:
            if isinstance(self.name, TemplateStr):
                name_value = self.name.template
                name = '<TemplateStr>'
            else:
                name_value = '<callable>'
                name = '<callable>'
            if context:
                name = self.render_name(context)
            elif self.id_:
                name = f'<{self.id_}>'

        if self.id_:
            id_ = f'id: {self.id_}, '
        else:
            id_ = ''
        return f'{name} = {self.__class__.__name__}({id_}{name}: {name_value})'

    def __repr__(self):
        return self._repr()

    def get_path(self, base_path: Path, context: Dict[str, Union[str, int]], override_path: Optional[Path] = None):
        """Get the object path. Can be overriden with the override_path (relative to the base path)."""
        if override_path:
            path = Path(base_path)/Path(override_path)
        else:
            path = Path(base_path) / self.render_name(context)
        return path

    def write(self, base_path: Path, context: Dict[str, Any], override_path: Optional[Path] = None):
        """Write the object to the appropriate path within the ``base_path``."""
        raise NotImplementedError()

    def dryrun(self, base_path: Path, context: Dict[str, Any], override_path: Optional[Path] = None):
        """Preview the file contents using the context."""
        raise NotImplementedError()

    def validate(self, base_path: Path, context: Dict[str, Any], override_path: Optional[Path] = None):
        """Validate the output against expected."""
        raise NotImplementedError()
