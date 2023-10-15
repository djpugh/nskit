"""Folder component."""
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from pydantic import Field, field_validator

from .file import File
from .filesystem_object import FileSystemObject


class Folder(FileSystemObject):
    """Folder component."""

    contents: List[Union[File, 'Folder']] = Field(default_factory=list, description='The folder contents')

    def write(self, base_path: Path, context: Dict[str, Any], override_path: Optional[Path] = None):
        """Write the rendered content to the appropriate path within the ``base_path``."""
        folder_path = self.get_path(base_path, context, override_path)
        folder_path.mkdir(exist_ok=True, parents=True)
        contents_dict = {}
        for obj in self.contents:
            contents_dict.update(obj.write(folder_path, context))
        return {folder_path: contents_dict}

    def dryrun(self, base_path: Path, context: Dict[str, Any], override_path: Optional[Path] = None):
        """Preview the file contents using the context."""
        folder_path = self.get_path(base_path, context, override_path)
        contents_dict = {}
        for u in self.contents:
            contents_dict.update(u.dryrun(folder_path, context))
        result = {folder_path: contents_dict}
        return result

    def validate(self, base_path: Path, context: Dict[str, Any], override_path: Optional[Path] = None):
        """Validate the output against expected."""
        missing = []
        errors = []
        ok = []
        path = self.get_path(base_path, context, override_path)
        if not path.exists():
            missing.append(path)
        for child in self.contents:
            child_missing, child_errors, child_ok = child.validate(path, context)
            missing += child_missing
            errors += child_errors
            ok += child_ok
        if not missing and not errors:
            ok.append(path)
        return missing, errors, ok

    @field_validator('contents', mode='before')
    @classmethod
    def _validate_contents_ids_unique(cls, contents):
        if contents:
            ids_ = []
            for item in contents:
                id_ = None
                if isinstance(item, FileSystemObject):
                    id_ = item.id_
                if isinstance(item, dict):
                    id_ = item.get('id_', None)
                if id_ is None:
                    # No id_ provided
                    continue
                if id_ in ids_:
                    raise ValueError(f'IDs for contents must be unique. The ID({id_}) already exists in the folder contents')
                ids_.append(id_)
        return contents

    def index(self, name_or_id):
        """Get the index of a specific file or folder given the name (or ID)."""
        for i, item in enumerate(self.contents):
            if item.id_ == name_or_id or item.name == name_or_id:
                return i
        raise KeyError(f'Name or id_ {name_or_id} not found in contents')

    def __getitem__(self, name_or_id):
        """Get the item by name or id."""
        index = self.index(name_or_id)
        return self.contents[index]

    def __setitem__(self, name_or_id, value):
        """Set an item by name or id."""
        try:
            index = self.index(name_or_id)
            self.contents.pop(index)
            self.contents.insert(index, value)
        except KeyError:
            self.contents.append(value)

    def _repr(self, context=None, indent=0, **kwargs):  # noqa: U100
        """Represent the contents of the folder."""
        indent_ = ' '*indent
        line_start = f'\n{indent_}|- '
        contents_repr = ''
        if self.contents:
            contents = sorted(self.contents, key=lambda x: isinstance(x, Folder))
            lines = [u._repr(context=context, indent=indent+2) for u in contents]
            contents_repr = ':'+line_start.join(['']+lines)
        return f'{super()._repr(context=context)}{contents_repr}'
