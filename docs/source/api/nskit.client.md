
::: nskit.client
    options:
        show_root_heading: False
        heading_level: 1

## ::: nskit.client.recipes.RecipeClient
    options:
        show_root_heading: True
        members:
            - list_recipes
            - get_recipe_versions
            - initialize_recipe

## ::: nskit.client.update.UpdateClient
    options:
        show_root_heading: True
        members:
            - check_update_available
            - update_project

## ::: nskit.client.discovery.DiscoveryClient
    options:
        show_root_heading: True
        members:
            - discover_recipes
            - get_recipe_info
            - get_recipe_versions

## Engines

### ::: nskit.client.engines.base.RecipeEngine
    options:
        show_root_heading: True
        members:
            - execute

### ::: nskit.client.engines.local.LocalEngine
    options:
        show_root_heading: True

### ::: nskit.client.engines.docker.DockerEngine
    options:
        show_root_heading: True

## Backends

### ::: nskit.client.backends.base.RecipeBackend
    options:
        show_root_heading: True

### ::: nskit.client.backends.local.LocalBackend
    options:
        show_root_heading: True

### ::: nskit.client.backends.github.GitHubBackend
    options:
        show_root_heading: True

### ::: nskit.client.backends.docker.DockerBackend
    options:
        show_root_heading: True

## Models

### ::: nskit.client.models.RecipeResult
    options:
        show_root_heading: True

### ::: nskit.client.models.UpdateResult
    options:
        show_root_heading: True

### ::: nskit.client.models.RecipeInfo
    options:
        show_root_heading: True

## Configuration

### ::: nskit.client.config.ConfigManager
    options:
        show_root_heading: True

### ::: nskit.client.config.RecipeConfig
    options:
        show_root_heading: True

## Exceptions

### ::: nskit.client.exceptions
    options:
        show_root_heading: True
