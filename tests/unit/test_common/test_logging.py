from logging import LoggerAdapter
import unittest

from logzero.jsonlogger import JsonFormatter

from nskit.common.logging import get_library_logger, get_logger, LibraryLoggerFactory


class LoggerTestCase(unittest.TestCase):

    def test_get_logger(self):
        self.assertIsInstance(get_logger('nskit.test'), LoggerAdapter)

    def test_logger_process(self):
        logger = get_logger('nskit.test')
        msg, extra = logger.process('abc', kwargs=dict(d=1, e=2))
        self.assertEqual(msg, 'abc')
        self.assertEqual(set(extra.keys()), {'exc_info', 'extra'})
        self.assertEqual(extra['extra']['extra'], {'d': 1, 'e': 2})

    def test_logger_json(self):
        logger = get_logger('nskit.test', config={'json_format': True})
        self.assertIsInstance(logger.logger.handlers[0].formatter, JsonFormatter)

    def test_logger_not_json(self):
        logger = get_logger('nskit.test', config={'json_format': False})
        self.assertNotIsInstance(logger.logger.handlers[0].formatter, JsonFormatter)

    def test_get_library_logger(self):
        logger = get_library_logger('nskit', '0.0.0', 'nskit.test')
        self.assertIsInstance(logger, LoggerAdapter)
        self.assertEqual(logger.extra, {'library': {'name': 'nskit', 'version': '0.0.0'}})


