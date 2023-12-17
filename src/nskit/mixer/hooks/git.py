"""Git hooks."""
from pathlib import Path
import subprocess  # nosec: B404
from typing import Any, Dict

from packaging.version import parse

from nskit._logging import logger_factory
from nskit.common.contextmanagers import ChDir
from nskit.mixer.components import Hook

logger = logger_factory.get(__name__)


class GitInit(Hook):
    """Git Hook to (re) initialise a repo."""

    def call(self, recipe_path: Path, context: Dict[str, Any]):
        """(re)initialise the repo."""
        with ChDir(recipe_path):
            logger.info('Initialising git repo')
            try:
                initial_branch_name = subprocess.check_output(['git', 'config', '--get', 'init.defaultBranch']).decode()  # nosec B607, B603
            except subprocess.CalledProcessError:
                initial_branch_name = None
            if not initial_branch_name:
                initial_branch_name = 'main'
            initial_branch_name = context.get('git', {}).get('initial_branch_name', initial_branch_name)
            # Check git version - new versions have --initial-branch arg on init
            version = subprocess.check_output(['git', 'version']).decode()  # nosec B607, B603
            version = version.replace('git version', '').lstrip()
            semver = parse('.'.join(version.split(' ')[0].split('.')[:3]))
            if semver >= parse('2.28.0'):
                subprocess.check_call(['git', 'init', '--initial-branch', initial_branch_name])  # nosec B607, B603
            else:
                subprocess.check_call(['git', 'init'])  # nosec B607, B603
                subprocess.check_call(['git', 'checkout', '-B', initial_branch_name])  # nosec B607, B603
            logger.info('Done')
