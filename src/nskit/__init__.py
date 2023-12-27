"""nskit.

Namespace development kit, helpful scaffolding for building python namespace repos (and other software).
"""


def __get_version() -> str:
    """Get version information or return default if unable to do so."""
    # Default
    default_version = '0+unknown'
    version = default_version
    # Development installation only
    try:
        # Look here for setuptools scm to update the version - for development environments only
        from setuptools_scm import get_version  # type: ignore
        try:
            version = get_version(root='../../', version_scheme='no-guess-dev', relative_to=__file__)
        except LookupError:
            pass
    except ImportError:
        pass
    # Development installation without setuptools_scm or installed package
    # try loading from file
    if version == default_version:
        try:
            from nskit._version import __version__  # noqa: F401
        except ImportError:
            pass
    # Development installation without setuptools_scm
    if version == default_version:
        # Use the metadata
        import sys
        if sys.version_info.major >= 3 and sys.version_info.minor >= 8:
            from importlib.metadata import PackageNotFoundError
            from importlib.metadata import version as parse_version
        else:
            from importlib_metadata import PackageNotFoundError
            from importlib_metadata import version as parse_version  # type: ignore
        try:
            version = parse_version("nskit")
        except PackageNotFoundError:
            # package is not installed
            pass
    return version


__version__ = __get_version()

from nskit.mixer import CodeRecipe, Recipe  # noqa: F401, E402
from nskit.recipes.python import PyRecipe, PyRepoMetadata  # noqa: F401, E402
from nskit.vcs import Codebase, Repo  # noqa: F401, E402
