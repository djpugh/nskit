"""Context manager for running in a specific directory."""
from contextlib import ContextDecorator
import os
from pathlib import Path
import tempfile
from typing import Optional
import warnings

from nskit._logging import logger_factory


class ChDir(ContextDecorator):
    """Context manager for running in a specified (or temporary) directory.

    The optional argument is a path to a specified target directory, if this isn't provided, a temporary directory is created
    """

    def __init__(self, target_dir: Optional[Path] = None):
        """Initialise the context manager.

        Keyword Args:
            target_dir (Optional[Path]): the target directory
        """
        self._temp_dir = None
        if not target_dir:
            # Handling circular imports with LoggingConfig
            logger_factory.get_logger(__name__).debug('No target_dir provided, using a temporary directory')
            self._temp_dir = tempfile.TemporaryDirectory()
            target_dir = self._temp_dir.name
        self.cwd = Path.cwd()
        self.target_dir = Path(target_dir)

    def __enter__(self):
        """Change to the target directory."""
        # Handling circular imports with LoggingConfig
        logger_factory.get_logger(__name__).info(f'Changing to {self.target_dir}')
        if not self.target_dir.exists():
            self.target_dir.mkdir()
        os.chdir(str(self.target_dir))
        if self._temp_dir:
            return self._temp_dir.__enter__()

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Reset to the original directory."""
        os.chdir(str(self.cwd))
        if self._temp_dir:
            try:
                self.target_dir.__exit__(exc_type, exc_val, exc_tb)
            except PermissionError as e:
                # Handling circular imports with LoggingConfig
                logger_factory.get_logger(__name__).warn('Unable to delete temporary directory.')
                warnings.warn(e, stacklevel=2)
