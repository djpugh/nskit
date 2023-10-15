

from pathlib import Path

from pydantic import Field

from nskit import __version__
from nskit.mixer import CodeRecipe, RepoMetadata


class PyRepoMetadata(RepoMetadata):

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

    @property
    def py_name(self):
        """Get python module name."""
        return '.'.join(self.name.split(self.repo_separator))

    @property
    def py_root(self):
        """Get root python module name."""
        return self.name.split(self.repo_separator)[0]

    @property
    def src_path(self):
        """Get module folder structure (src not included)."""
        return Path(*self.name.split(self.repo_separator)).as_posix()

    @property
    def module_depth(self) -> int:
        return len(self.name.split(self.repo_separator))


class PyRecipe(CodeRecipe):
    """Base recipe for python recipes."""

    version: str = __version__
    repo: PyRepoMetadata = Field(..., description='Python repo information')

    @staticmethod
    def _to_pep8(value):
        return str(value).lower().replace(' ', '_').replace('-', '_')

    def model_post_init(self, *args):  # noqa: U100
        """Set repo name handling."""
        self.repo.name = self.name
