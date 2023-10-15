"""Jinja2 Monkey patching for pkg resource loader and prepend extension."""
from jinja2 import BaseLoader, ChoiceLoader, Environment,  TemplateNotFound

from ..utilities import load_resource


class _PkgResourcesTemplateLoader(BaseLoader):
    """Load jinja templates via pkg_resources."""

    @staticmethod
    def get_source(environment, template):  # noqa: U100
        """Get the source using pkg_resources."""
        if ':' not in template:
            raise TemplateNotFound(template)
        pkg, resource = template.split(':')
        source = load_resource(pkg, resource)
        return source, None, lambda: True


JINJA_ENVIRONMENT = Environment(loader=ChoiceLoader([_PkgResourcesTemplateLoader()]))  # nosec B701
