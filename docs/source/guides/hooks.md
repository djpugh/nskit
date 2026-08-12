# Hooks

Hooks are pre/post-processing steps that run during recipe creation. They execute before template rendering (pre-hooks) or after file writing (post-hooks), and can modify the output path, template context, or even the recipe's contents.

## How Hooks Work

A hook is a Pydantic model that implements the `call()` method:

```python
from pathlib import Path
from typing import Any, Optional

from nskit.mixer.components.hook import Hook


class MyHook(Hook):
    """A custom hook."""

    def call(self, recipe_path: Path, context: dict[str, Any], **kwargs) -> Optional[tuple[Path, dict]]:
        # Do something
        return (recipe_path, context)  # or None to keep unchanged
```

When `Recipe.create()` runs, it calls each hook in sequence:

```
pre_hooks → template rendering → post_hooks
```

Each hook receives:

- `recipe_path` — where the recipe will be (pre) or was (post) written
- `context` — the template rendering context
- `recipe` (via kwargs) — the Recipe instance itself

Return `None` to keep path/context unchanged, or `(recipe_path, context)` to modify them.

## The `recipe` Kwarg

Hooks receive the recipe instance as `recipe=self` when called from `Recipe.create()`. This enables hooks to introspect or mutate the recipe — for example, adding files to `contents` before rendering.

```python
class InjectFileHook(Hook):
    """Add a file to the recipe before rendering."""

    filename: str = "GENERATED.md"
    content: str = "# Auto-generated\n"

    def call(self, recipe_path: Path, context: dict[str, Any], recipe=None):
        if recipe is not None:
            from nskit.mixer.components.file import File
            recipe.contents.append(
                File(id_="generated", name=self.filename, content=self.content)
            )
        return (recipe_path, context)
```

Use this in a pre-hook to dynamically add or modify recipe contents based on runtime conditions.

## Backwards Compatibility

Existing hooks that only accept `(recipe_path, context)` continue to work. The `Hook.__call__` method inspects the `call()` signature and only forwards kwargs that the method accepts:

```python
# Old-style — still works, recipe kwarg is silently dropped
class LegacyHook(Hook):
    def call(self, recipe_path, context):
        return None

# New-style — receives the recipe instance
class ModernHook(Hook):
    def call(self, recipe_path: Path, context: dict[str, Any], **kwargs):
        recipe = kwargs.get("recipe")
        return None

# Explicit param — also works, only 'recipe' is forwarded
class ExplicitHook(Hook):
    def call(self, recipe_path: Path, context: dict[str, Any], recipe=None):
        return None
```

All three styles can coexist in the same recipe's hook list.

## Built-in Hooks

### GitInit

Initialises a git repository in the generated project directory.

```python
from nskit.mixer.hooks.git import GitInit

class MyRecipe(Recipe):
    post_hooks = [GitInit()]
```

Respects `context["git"]["initial_branch_name"]` for the initial branch (defaults to `main`). Handles git versions before and after 2.28.0 (which introduced `--initial-branch`).

### PrecommitInstall

Installs pre-commit hooks if a `.pre-commit-config.yaml` exists.

```python
from nskit.mixer.hooks.pre_commit import PrecommitInstall

class MyRecipe(Recipe):
    post_hooks = [GitInit(), PrecommitInstall()]
```

Tries `pip install pre-commit` first, falls back to `uv pip install pre-commit`. Skips gracefully if neither is available.

### CleanupHook

Removes empty files and/or empty directories after rendering. Useful when conditional templates render to nothing.

```python
from nskit.mixer.hooks.cleanup import CleanupHook

class MyRecipe(Recipe):
    post_hooks = [CleanupHook()]
```

Configuration options:

| Field | Default | Description |
|-------|---------|-------------|
| `remove_empty_files` | `True` | Remove 0-byte and whitespace-only files |
| `remove_empty_dirs` | `True` | Remove empty directories |
| `skip_gitkeep` | `True` | Preserve empty `.gitkeep` files |

Individual hooks are also available:

```python
from nskit.mixer.hooks.cleanup import RemoveEmptyFilesHook, RemoveEmptyDirectoriesHook
```

## Writing a Custom Hook

Hooks are Pydantic models, so you can declare configurable fields:

```python
class LoggingHook(Hook):
    """Post-hook that logs the generated file tree."""

    log_file: str = "generation.log"

    def call(self, recipe_path: Path, context: dict[str, Any], **kwargs):
        files = list(recipe_path.rglob("*"))
        log_path = recipe_path / self.log_file
        log_path.write_text("\n".join(str(f.relative_to(recipe_path)) for f in files))
        return None
```

```python
class MyRecipe(Recipe):
    post_hooks = [LoggingHook(log_file="manifest.txt")]
```

## Pre-hook vs Post-hook

| Aspect | Pre-hook | Post-hook |
|--------|----------|-----------|
| Runs | Before template rendering | After files are written |
| `recipe_path` | Target directory (may not exist yet) | Actual written directory |
| Can modify contents | Yes (via `recipe.contents`) | No (files already written) |
| Use cases | Context injection, path rewriting, conditional content | Git init, pre-commit, cleanup, validation |

## Ordering

Hooks execute in list order. Each hook sees the result of the previous one:

```python
class MyRecipe(Recipe):
    pre_hooks = [ContextSetupHook(), ContentInjectionHook()]
    post_hooks = [CleanupHook(), GitInit(), PrecommitInstall()]
```

## Using in CodeRecipe

The `CodeRecipe` base class (for git-tracked code repos) defaults to `post_hooks=[GitInit()]`:

```python
from nskit.mixer.repo import CodeRecipe

class MyCodeRecipe(CodeRecipe):
    # GitInit is already included. Add more:
    post_hooks = [GitInit(), CleanupHook(), PrecommitInstall()]
```
