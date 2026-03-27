::: nskit.vcs
    options:
        show_root_heading: False
        heading_level: 1

## Repositories

### ::: nskit.vcs.repo.Repo
    options:
        show_root_heading: True
        members:
            - name
            - local_dir
            - create
            - clone
            - push
            - pull
            - commit
            - install
            - exists_locally

### ::: nskit.vcs.repo.NamespaceValidationRepo
    options:
        show_root_heading: True
        members:
            - name
            - namespaces_filename
            - validator
            - validate_name
            - create

## Namespace Validation

### ::: nskit.vcs.namespace_validator.NamespaceValidator
    options:
        show_root_heading: True
        members:
            - options
            - repo_separator
            - delimiters
            - validate_name
            - to_parts
            - to_repo_name

### ::: nskit.vcs.namespace_validator.NamespaceOptionsType
    options:
        show_root_heading: True

### ::: nskit.vcs.namespace_validator.ValidationEnum
    options:
        show_root_heading: True

## Installers

### ::: nskit.vcs.installer.PythonInstaller
    options:
        show_root_heading: True

## Provider Detection

### ::: nskit.vcs.provider_detection.get_default_repo_client
    options:
        show_root_heading: True

## Providers

### ::: nskit.vcs.providers.abstract.RepoClient
    options:
        show_root_heading: True

### ::: nskit.vcs.providers.abstract.VCSProviderSettings
    options:
        show_root_heading: True

### ::: nskit.vcs.providers.github.GithubSettings
    options:
        show_root_heading: True
