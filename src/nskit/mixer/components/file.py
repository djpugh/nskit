"""File component."""
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Union

from pydantic import Field

from nskit.mixer.components.filesystem_object import FileSystemObject
from nskit.mixer.utilities import JINJA_ENVIRONMENT_FACTORY, Resource


class File(FileSystemObject):
    """File component."""

    content: Union[Resource, str, bytes, Path, Callable] = Field('', description='The file content')

    def render_content(self, context: Dict[str, Any]):  # pylint: disable=arguments-differ
        """Return the rendered content using the context and the Jinja environment."""
        if context is None:
            context = {}
        if isinstance(self.content, Resource):
            content = self.content.load()
        elif isinstance(self.content, Path):
            with open(self.content) as f:
                content = f.read()
        elif isinstance(self.content, Callable):
            content = self.content(context)
        else:
            content = self.content
        if isinstance(content, str):
            # If it is a string, we render the content
            content = JINJA_ENVIRONMENT_FACTORY.environment.from_string(content).render(**context)
        return content

    def write(self, base_path: Path, context: Dict[str, Any], override_path: Optional[Path] = None):
        """Write the rendered content to the appropriate path within the ``base_path``."""
        file_path = self.get_path(base_path, context, override_path)
        content = self.render_content(context)
        response = {}
        if content is not None:
            if isinstance(content, str):
                open_str = 'w'
            elif isinstance(content, bytes):
                open_str = 'wb'
            with file_path.open(open_str) as output_file:
                output_file.write(content)
            response[file_path] = content
        return response

    def dryrun(self, base_path: Path, context: Dict[str, Any], override_path: Optional[Path] = None):
        """Preview the file contents using the context."""
        file_path = self.get_path(base_path, context, override_path)
        content = self.render_content(context)
        result = {}
        if content is not None:
            result[file_path] = content
        return result

    def validate(self, base_path: Path, context: Dict[str, Any], override_path: Optional[Path] = None):
        """Validate the output against expected."""
        missing = []
        errors = []
        ok = []
        path = self.get_path(base_path, context, override_path)
        content = self.render_content(context)
        if content is not None:
            if not path.exists():
                missing.append(path)
            else:
                if isinstance(content, bytes):
                    read_str = 'rb'
                else:
                    read_str = 'r'
                with open(path, read_str) as f:
                    if f.read() != self.render_content(context):
                        errors.append(path)
                    else:
                        ok.append(path)
        return missing, errors, ok
