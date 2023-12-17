"""The base recipe object."""
import datetime as dt
import inspect
from pathlib import Path
import sys
from typing import List, Optional

from pydantic import BaseModel, Field

from nskit import __version__
from nskit.common.extensions import get_extension_names, load_extension
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
    extension_name: Optional[str] = Field(None, description="The name of the recipe as an extension to load.")

    @property
    def recipe(self):
        """Recipe context."""
        extension_name = self.extension_name
        if extension_name is None:
            extension_name = self.__class__.__name__
        return {'name': f'{self.__class__.__module__}:{self.__class__.__name__}', 'version': self.version, 'extension_name': extension_name}

    def create(self, base_path: Optional[Path] = None, override_path: Optional[Path] = None, **additional_context):
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
        content = self.write(recipe_path.parent, context, override_path=recipe_path.name)
        recipe_path = list(content.keys())[0]
        for hook in self.post_hooks:
            recipe_path, context = hook(recipe_path, context)
        self._write_batch(Path(recipe_path))
        return {Path(recipe_path): list(content.values())[0]}

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
        if sys.version_info.major <= 3 and sys.version_info.minor < 11:
            creation_time = dt.datetime.now().astimezone()
        else:
            creation_time = dt.datetime.now(dt.UTC).isoformat()
        return {'context': self.__dump_context(ser=True),
                'nskit_version': __version__,
                'creation_time': creation_time,
                'recipe': self.recipe}

    @property
    def context(self):
        """Get the context on the initialised recipe."""
        # This inherits (via FileSystemObject) from nskit.common.configuration:BaseConfiguration, which includes properties in model dumps
        return self.__dump_context()

    def __dump_context(self, ser=False):
        # Make sure it is serialisable if required
        if ser:
            mode = 'json'
        else:
            mode = 'python'
        context = self.model_dump(
            mode=mode,
            exclude={
                'context',
                'contents',
                'name',
                'id_',
                'post_hooks',
                'pre_hooks',
                'version',
                'recipe_batch',
                'recipe',
                'extension_name',
                }
            )
        context.update({'recipe': self.recipe})
        return context

    def __repr__(self):
        """Repr(x) == x.__repr__."""
        context = self.context
        return f'{self._repr(context=context)}\n\nContext: {context}'

    def dryrun(
            self,
            base_path: Optional[Path] = None,
            override_path: Optional[Path] = None,
            **additional_context):
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
            **additional_context):
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
            raise ValueError(f'Recipe {recipe_name} not found, it may be mis-spelt or not installed. Available recipes: {get_extension_names(RECIPE_ENTRYPOINT)}')
        recipe = recipe_klass(**kwargs)
        recipe.extension_name = recipe_name
        return recipe

    @staticmethod
    def inspect(recipe_name: str, include_private: bool = False, include_folder: bool = False, include_base: bool = False):
        """Get the fields on a recipe as an extension."""
        recipe_klass = load_extension(RECIPE_ENTRYPOINT, recipe_name)
        if recipe_klass is None:
            raise ValueError(f'Recipe {recipe_name} not found, it may be mis-spelt or not installed. Available recipes: {get_extension_names(RECIPE_ENTRYPOINT)}')
        sig = Recipe._inspect_basemodel(recipe_klass, include_private=include_private)
        if not include_folder:
            folder_sig = inspect.signature(Folder)
            params = [v for u, v in sig.parameters.items() if u not in folder_sig.parameters.keys() or u == 'name']
            sig = sig.replace(parameters=params)
        if not include_base:
            recipe_sig = inspect.signature(Recipe)
            params = [v for u, v in sig.parameters.items() if u not in recipe_sig.parameters.keys() or u == 'name']
            sig = sig.replace(parameters=params)
        return sig

    @staticmethod
    def _inspect_basemodel(kls, include_private: bool = False):
        sig = inspect.signature(kls)
        # we need to drop the private params
        params = []
        for u, v in sig.parameters.items():
            if not include_private and u.startswith('_'):
                continue
            if isinstance(v.annotation, type) and issubclass(v.annotation, BaseModel):
                params.append(v.replace(default=Recipe._inspect_basemodel(v.annotation, include_private=include_private)))
            else:
                params.append(v)
        return sig.replace(parameters=params, return_annotation=kls)
