# nskit

``nskit`` is a python package that provides useful utilities and implementations for creating and managing a namespaced codebase for python and other programming languages.

It includes:

* [nskit.mixer][] provides a [jinja2](https://jinja.palletsprojects.com/en/3.1.x/) based composable template system that can be adapted to any programming language
* [nskit.recipes][] provides some initial recipes for repositories (using [nskit.mixer][]), including:
    - ``python_package`` - a python package including namespace structures
    - ``python_api_service`` - a python api service including namespace structures
    - ``recipe`` - a recipe for creating a new recipe
* [nskit.vcs][] providing some simple interfaces for working with a Version Control System, and creating/managing repositories, cloning the code base etc.

Find out how to [use it here][using-nskit]