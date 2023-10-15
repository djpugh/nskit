"""Jinja2 Monkey patching for pkg resource loader and prepend extension."""
from jinja2 import BaseLoader, ChoiceLoader, Environment,  TemplateNotFound
from pydantic import ValidationError

from ..utilities import Resource


class _PkgResourcesTemplateLoader(BaseLoader):
    """Load jinja templates via pkg_resources."""

    @staticmethod
    def get_source(environment, template):  # noqa: U100
        """Get the source using pkg_resources."""
        try:
            Resource.validate(template)
        except ValidationError as e:
            raise TemplateNotFound(template, *e.args)
        resource = Resource(template)
        try:
            source = resource.load()
        except FileNotFoundError:
            raise TemplateNotFound(template)
        return source, None, lambda: True


JINJA_ENVIRONMENT = Environment(loader=ChoiceLoader([_PkgResourcesTemplateLoader()]))  # nosec B701
