"""The base recipe object."""
import datetime as dt
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import Field

from nskit import __version__
from nskit.common.extensions import load_extension
from nskit.common.io import yaml
from nskit.mixer.components.folder import Folder
from nskit.mixer.components.hook import Hook



RECIPE_ENTRYPOINT = 'nskit.recipes'


class Recipe(Folder):
    """The base Recipe object.

    A Recipe is a folder, with additional methods for handling context for the Jinja templating.
    It also includes hooks that can be run before rendering (``pre-hooks``) e.g. checking or changing values,
    and after (``post-hooks``) e.g. running post-generation steps.
    """
    _extension_name: Optional[str] = None

    name: str = Field(None, validate_default=True, description='The repository name')
    version: Optional[str] = Field(None, description='The recipe version')  # type: ignore
    pre_hooks: List[Hook] = Field(
        default_factory=list,
        validate_default=True,
        description='Hooks that can be used to modify a recipe path and context before writing'
    )
    post_hooks: List[Hook] = Field(
        default_factory=list,
        validate_default=True,
        description='Hooks that can be used to modify a recipe path and context after writing'
    )

    @property
    def recipe(self):
        """Recipe context."""
        return {'name': f'{self.__class__.__module__}:{self.__class__.__name__}', 'version': self.version, 'extension_name': self.extension_name}

    @property
    def extension_name(self):
        """Get the entrypoint name."""
        if self._extension_name is not None:
            return self._extension_name
        else:
            return self.__class__.__name__

    @extension_name.setter
    def extension_name(self, value):
        self._extension_name = value

    def create(self, base_path: Optional[Path] = None, override_path: Optional[Path]=None, **additional_context):
        """Create the recipe.

        Use the configured parameters and any additional context as kwargs to create the recipe at the
        base path (or current directory if not provided).
        """
        if base_path is None:
            base_path = Path.cwd()
        else:
            base_path = Path(base_path)
        context = self.context
        context.update(additional_context)
        recipe_path = self.get_path(base_path, context, override_path=override_path)
        for hook in self.pre_hooks:
            recipe_path, context = hook(recipe_path, context)
        recipe_path = self.write(recipe_path.parent, context, override_path=recipe_path.name)
        for hook in self.post_hooks:
            recipe_path, context = hook(recipe_path, context)
        self._write_batch(Path(recipe_path))
        return Path(recipe_path)

    def _write_batch(self, folder_path: Path):
        """Write out the parameters used.

        When we use this we want to keep track of what parameters were used to enable rerunning.
        This methods writes this into the generated folder as a YAML file.
        """
        batch_path = Path(folder_path)/'.recipe-batch.yaml'
        if batch_path.exists():
            with batch_path.open() as f:
                batch = yaml.loads(f.read())
        else:
            batch = []
        batch.append(self.recipe_batch)
        with batch_path.open('w') as f:
            f.write(yaml.dumps(batch))

    @property
    def recipe_batch(self):
        """Get information about the specific info of this recipe."""
        return {'context': self.context,
                'nskit_version': __version__,
                'creation_time': dt.datetime.now(dt.UTC).isoformat(),
                'recipe': self.recipe}

    @property
    def context(self):
        """Get the context on the initialised recipe."""
        # This inherits (via FileSystemObject) from nskit.common.configuration:BaseConfiguration, which includes properties in model dumps
        context = self.model_dump(exclude={'context',
                                           'contents',
                                           'name',
                                           'id_',
                                           'post_hooks',
                                           'pre_hooks',
                                           'version',
                                           'recipe_batch',
                                           'recipe',
                                           'extension_name',
                                           })
        return context

    def __repr__(self):
        """Repr(x) == x.__repr__."""
        context = self.context
        return f'{self._repr(context=context)}\n\nContext: {context}'

    def dryrun(
            self,
            base_path: Optional[Path] = None,
            override_path: Optional[Path] = None,
            **additional_context
        ):
        """See the recipe as a dry run."""
        combined_context = self.context
        combined_context.update(additional_context)
        if base_path is None:
            base_path = Path.cwd()
        return super().dryrun(base_path=base_path, context=combined_context, override_path=override_path)

    def validate(
            self,
            base_path: Optional[Path] = None,
            override_path: Optional[Path] = None,
            **additional_context
        ):
        """Validate the created repo."""
        combined_context = self.context
        combined_context.update(additional_context)
        if base_path is None:
            base_path = Path.cwd()
        return super().validate(base_path=base_path, context=combined_context, override_path=override_path)

    @staticmethod
    def load(recipe_name: str, **kwargs):
        """Load a recipe as an extension."""
        recipe_klass = load_extension(RECIPE_ENTRYPOINT, recipe_name)
        if recipe_klass is None:
            raise ValueError(f'Recipe {recipe_name} not found, it may be mis-spelt or not installed')
        recipe = recipe_klass(**kwargs)
        recipe.extension_name = recipe_name
        return recipe
