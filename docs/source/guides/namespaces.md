# Working with Namespaces

If your organisation has more than a handful of repos, you've probably wished someone would enforce a naming convention. nskit can do that.

## What Are Namespaces?

A namespace defines the allowed structure for repository names:

```yaml
# namespaces.yaml
options:
  - platform:
      - auth:
          - service
          - library
      - data:
          - pipeline
          - warehouse
  - mobile:
      - ios
      - android
delimiters: ["-", ".", ","]
repo_separator: "-"
```

This allows `platform-auth-service-users` and `mobile-ios-app`, but rejects `yolo-my-project`.

## Validating Names

```python
from nskit.vcs.namespace_validator import NamespaceValidator

validator = NamespaceValidator(
    options=[{'platform': ['auth', 'data']}, 'shared'],
    repo_separator='-',
)

result, msg = validator.validate_name('platform-auth-users')
# True, 'ok'

result, msg = validator.validate_name('rogue-project')
# False, 'Does not match valid names for <root>: ...'
```

## Setting Up a Namespace Repo

The rules live in a dedicated git repo that can be shared across your organisation:

```python
from nskit.vcs.repo import NamespaceValidationRepo

ns_repo = NamespaceValidationRepo(local_dir=Path('.namespaces'))
ns_repo.create(
    namespace_options=[
        {'platform': [
            {'auth': ['service', 'library']},
            {'data': ['pipeline', 'warehouse']},
        ]},
        {'mobile': ['ios', 'android']},
    ],
    repo_separator='-',
)
```

## Name Conversion

Delimiters (`.`, `-`, `,`) are interchangeable. nskit normalises them:

| Input | Repo Name | Python Module | Folder Structure |
|-------|-----------|---------------|-----------------|
| `platform.auth.users` | `platform-auth-users` | `platform.auth.users` | `platform/auth/users/` |
| `platform-auth-users` | `platform-auth-users` | `platform.auth.users` | `platform/auth/users/` |

## Integration with Platform

Namespaces are typically used alongside a VCS provider to validate names before creating repos. See [Platform Integration](platform-integration.md) for how to wire this together.
