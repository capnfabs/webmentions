import unittest
from webmentions import db
from webmentions.db.models import DiscoveryFeed


class TestConfig(unittest.TestCase):

    def test_readonly_session_explicit_flush(self):
        with db.readonly_session() as session:
            discovery_feed = DiscoveryFeed(
                submitted_url='trash',
                discovered_feed='trash',
                feed_type_when_discovered='trash'
            )
            session.add(discovery_feed)
            try:
                session.flush()
            except Exception as ex:
                assert "readonly session, stop modifying things please" in str(ex)

    def test_readonly_session_context_exit(self):
        progress_marker = False
        received_exception = None
        try:
            with db.readonly_session() as session:
                discovery_feed = DiscoveryFeed(
                    submitted_url='trash',
                    discovered_feed='trash',
                    feed_type_when_discovered='trash'
                )
                session.add(discovery_feed)
                progress_marker = True
        except Exception as ex:
            received_exception = ex

        assert progress_marker, "Expected to make it to end of block"
        assert received_exception, "Expected to receive exception"
        assert "readonly session, stop modifying things please" in str(received_exception)
