::: nskit.mixer
    options:
        show_root_heading: False

## Components

### ::: nskit.mixer.components.file.File
    options:
        show_root_heading: True

### ::: nskit.mixer.components.folder.Folder
    options:
        show_root_heading: True

### ::: nskit.mixer.components.recipe.Recipe
    options:
        show_root_heading: True
        inherited_members: true
        members:
            - name
            - version
            - contents
            - pre_hooks
            - post_hooks
            - extension_name
            - context
            - create
            - dryrun
            - validate
            - load
            - inspect

### ::: nskit.mixer.components.recipe.RecipeField
    options:
        show_root_heading: True

### ::: nskit.mixer.components.hook.Hook
    options:
        show_root_heading: True

### ::: nskit.mixer.components.license_file.LicenseFile
    options:
        show_root_heading: True

### ::: nskit.mixer.components.license_file.LicenseOptionsEnum
    options:
        show_root_heading: True

## Repo Metadata

### ::: nskit.mixer.repo.CodeRecipe
    options:
        show_root_heading: True

### ::: nskit.mixer.repo.RepoMetadata
    options:
        show_root_heading: True

## Hooks

### ::: nskit.mixer.hooks.git.GitInit
    options:
        show_root_heading: True

### ::: nskit.mixer.hooks.pre_commit.PrecommitInstall
    options:
        show_root_heading: True

## Utilities

### ::: nskit.mixer.utilities.Resource
    options:
        show_root_heading: True
