::: nskit.mixer
    options:
        show_root_heading: False



## nskit.mixer.components
### ::: nskit.mixer.components
    options:
        show_root_heading: False
        members:
            - File
            - Folder
            - Hook
            - LicenseFile
            - LicenseOptionsEnum
            - Recipe

### nskit.mixer.components.license_file
#### ::: nskit.mixer.components.license_file
    options:
        show_root_heading: False
        members:
            - get_license_filename
            - get_license_content

## nskit.mixer.repo
### ::: nskit.mixer.repo
    options:
        show_root_heading: False
        members:
            - CodeRecipe
            - RepoMetadata

## nskit.mixer.hooks
### ::: nskit.mixer.hooks
    options:
        show_root_heading: False
#### nskit.mixer.hooks.git
##### ::: nskit.mixer.hooks.git
    options:
        show_root_heading: False
#### nskit.mixer.hooks.pre_commit
##### ::: nskit.mixer.hooks.pre_commit
    options:
        show_root_heading: False
