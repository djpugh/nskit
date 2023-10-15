"""Logger Adaptor with JSON and extra handling."""
from functools import wraps
from logging import LoggerAdapter

from logzero import setup_logger

from .config import DEFAULT_LOGLEVEL


class Logger(LoggerAdapter):
    """LoggerAdapter to handle extra variables nicely for common logging."""

    def process(self, msg, kwargs):
        """Process the extra variables.

        Add any extra kwargs into the record as a sub-dictionary called extra for the log.
        Also add exc_info into the record if provided.
        """
        exc_info = kwargs.pop('exc_info', None)
        kwargs['extra'] = kwargs.get('extra', {})
        extra = self.extra.copy()
        extra.update(kwargs.pop('extra', {}))
        extra.update(kwargs)
        return msg, {'extra': {'extra': extra}, 'exc_info': exc_info}

    def log_return(self, msg=None, level=DEFAULT_LOGLEVEL, **logger_kwargs):
        """Return a decorator which logs the outputs of a function."""

        def wrapper_factory(fn):
            """Build the wrapper."""

            @wraps(fn)
            def wrapper(*args, **kwargs):
                nonlocal msg, logger_kwargs
                if msg is None:
                    msg = fn.__qualname__
                result = fn(*args, **kwargs)
                getattr(self, level.lower())(msg, result=result, **logger_kwargs)
                return result

            return wrapper

        return wrapper_factory

    def log_inputs(self, msg=None, level=DEFAULT_LOGLEVEL, **logger_kwargs):
        """Return a decorator which logs the inputs of a function."""

        def wrapper_factory(fn):

            @wraps(fn)
            def wrapper(*args, **kwargs):
                nonlocal msg, logger_kwargs
                if msg is None:
                    msg = fn.__qualname__
                getattr(self, level.lower())(msg, inputs=(args, kwargs), **logger_kwargs)
                return fn(*args, **kwargs)

            return wrapper

        return wrapper_factory


def get_logger(name, config=None, **kwargs):
    """Get the logger object.

    You can set the json flag for json logging (or this can be set globally for all logs if required, using the LOG_JSON env var.).
    """
    if config is None:
        config = {}
    if isinstance(config, dict):
        from .config import LoggingConfig
        logging_config = LoggingConfig(**config)
    else:
        logging_config = config
    logger = setup_logger(name, **logging_config.model_dump(by_alias=True, exclude={'format_string', 'extra'}), **kwargs)
    return Logger(logger, extra=logging_config.extra)
