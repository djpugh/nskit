"""LoggingFormatter with extra."""
from logzero import LogFormatter as _LogFormatter

BASE_FORMAT_STR = '%(color)s %(levelname)s: %(name)s - %(asctime)-15s: %(message)s - %(extra)s :: %(filename)s:%(funcName)s'  # noqa: E501


class LoggingFormatter(_LogFormatter):
    """Add extra to record."""

    def format(self, record):
        """Format the record with extra attribute."""
        record.extra = getattr(record, 'extra', {})
        return super().format(record)


def get_library_log_format_string(library, version):
    """Get a log format string including the library name and version."""
    return BASE_FORMAT_STR.replace('%(name)s', f'{library}:{version} - %(name)s')
