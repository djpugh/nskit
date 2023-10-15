"""Common utilities for nskit."""

# Lazy imports
from . import lazy as __lazy

configuration = __lazy.lazy_import('nskit.common.configuration')
contextmanagers = __lazy.lazy_import('nskit.common.contextmanagers')
extensions = __lazy.lazy_import('nskit.common.extensions')
io = __lazy.lazy_import('nskit.common.io')
logging = __lazy.lazy_import('nskit.common.logging')
