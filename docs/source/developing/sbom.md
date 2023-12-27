# Software Bill of Materials

``nskit`` is licensed under the [MIT License](license.md).

The dependencies for ``nskit`` are:

## Runtime Dependencies

These are the dependencies used for running ``nskit``:

### ::licenseinfo

### Extras:

#### Github
##### ::licenseinfo
    using: PEP631:github
    diff: PEP631

#### Azure Devops
##### ::licenseinfo
    using: PEP631:azure_devops
    diff: PEP631

## Development Dependencies

These are dependencies used for development (e.g. testing, linting etc.) of ``nskit``:

### ::licenseinfo
    using: PEP631:dev
    diff: PEP631

### Test Dependencies
#### ::licenseinfo
    using: PEP631:dev;dev-test
    diff: PEP631:dev

### Lint Dependencies
#### ::licenseinfo
    using: PEP631:dev;dev-lint
    diff: PEP631:dev

### Security Dependencies
#### ::licenseinfo
    using: PEP631:dev;dev-security
    diff: PEP631:dev

### Docs Dependencies
#### ::licenseinfo
    using: PEP631:dev;dev-docs
    diff: PEP631:dev

### Build Dependencies
#### ::licenseinfo
    using: PEP631:dev;dev-build
    diff: PEP631:dev
