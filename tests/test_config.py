import unittest
from webmentions import config

class TestConfig(unittest.TestCase):

    def test_echo_sql_off(self):
        assert config.ECHO_SQL is False, "Don't check in code with ECHO_SQL=True"
