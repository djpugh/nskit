"""Python Recipes."""
from pathlib import Path
import re

from pydantic import Field

from nskit import __version__
from nskit.mixer import CodeRecipe, RepoMetadata

_DELIMITERS = ['.', ',', '-']


class PyRepoMetadata(RepoMetadata):
    """Repo Metadata for python templates."""

    _name: str = None

    @property
    def name(self):
        """Get repo name."""
        return self._name

    @name.setter
    def name(self, value):
        """Set repo name."""
        if isinstance(value, str):
            self._name = value

    def _get_name_parts(self):
        return re.split('|'.join(map(re.escape, list(set(_DELIMITERS+[self.repo_separator])))), self.name)

    @property
    def py_name(self):
        """Get python module name."""
        return '.'.join(self._get_name_parts())

    @property
    def py_root(self):
        """Get root python module name."""
        return self._get_name_parts()[0]

    @property
    def src_path(self):
        """Get module folder structure (src not included)."""
        return Path(*self._get_name_parts()).as_posix()

    @property
    def module_depth(self) -> int:
        """Get the module depth.

        ``a.b.c`` has a depth of 3, ``a`` has a depth of 1
        """
        return len(self._get_name_parts())


class PyRecipe(CodeRecipe):
    """Base recipe for python recipes."""

    version: str = __version__
    """Version of the recipe."""

    repo: PyRepoMetadata = Field(...)
    """Python repo metadata."""

    @staticmethod
    def _to_pep8(value):
        return str(value).lower().replace(' ', '_').replace('-', '_')

    def model_post_init(self, *args):  # noqa: U100
        """Set repo name handling."""
        self.repo.name = self.name
