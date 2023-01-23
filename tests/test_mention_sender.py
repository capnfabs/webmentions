import contextlib
import unittest
from typing import ContextManager

import requests_mock

from webmentions.scanner import mention_sender
from webmentions.scanner.mention_detector import MentionCapabilities
from webmentions.scanner.mention_sender import MentionCandidate


class TestMentionSender(unittest.TestCase):

    def enter_context(self, context: ContextManager) -> None:
        self._context_stack.enter_context(context)

    def setUp(self) -> None:
        self._context_stack = contextlib.ExitStack()

        self.requests = requests_mock.Mocker()
        self.enter_context(self.requests)

    def tearDown(self) -> None:
        self._context_stack.close()

    def test_handle_error(self):
        error_response = """
    <?xml version="1.0" encoding="UTF-8"?>
    <methodResponse>
      <fault>
        <value>
          <struct>
            <member>
              <name>faultCode</name>
              <value><int>0</int></value>
            </member>
            <member>
              <name>faultString</name>
              <value><string>Invalid discovery target</string></value>
            </member>
          </struct>
        </value>
      </fault>
    </methodResponse>
    """.strip()
        PINGBACK_URL = "https://potato.canon/xmlrpc.php"
        self.requests.post(PINGBACK_URL, text=error_response)
        mc = MentionCandidate(
            'https://my.home.page/have-you-heard-about-potatos',
            'https://yolo.potato/blog-post', MentionCapabilities(
                webmention_url=None,
                pingback_url=PINGBACK_URL
            )
        )
        try:
            mention_sender.send_mention(mc)
            assert False, 'expected exception'
        except mention_sender.RemoteError as err:
            assert err.code == 0
            assert err.message == 'Invalid discovery target'

    def test_pingback_success(self):
        success_response = """
    <?xml version="1.0" encoding="UTF-8"?>
    <methodResponse>
      <params>
        <param>
          <value>
          <string>Pingback from https://grand-phoenix-d50fd5.netlify.app/posts/test_pingback/ to https://pingbacktest08.wordpress.com/2023/01/22/the-human-condition-by-hannah-arendt/ registered. Keep the web talking! :-)</string>
          </value>
        </param>
      </params>
    </methodResponse>
    """
        PINGBACK_URL = "https://potato.canon/xmlrpc.php"
        self.requests.post(PINGBACK_URL, text=success_response)
        mc = MentionCandidate(
            'https://my.home.page/have-you-heard-about-potatos',
            'https://yolo.potato/blog-post', MentionCapabilities(
                webmention_url=None,
                pingback_url=PINGBACK_URL
            )
        )
        # expect no exception
        mention_sender.send_mention(mc)


def test_build_pingback_xml():
    mc = MentionCandidate(
        mentioner_url='https://sender.potato', mentioned_url='https://destination.potato',
        capabilities=MentionCapabilities(
            webmention_url=None,
            pingback_url='https://pingback.example/xmlrpc.lol',
        ),
    )
    output = mention_sender._build_pingback_xml(mc).strip()

    # this is brittle to changes in lxml's formatter, but it's much easier to compare string diffs
    # than xml diffs
    expected_xml = """
<?xml version='1.0' encoding='utf-8'?>
<methodCall>
  <methodName>pingback.ping</methodName>
  <params>
    <param>
      <value>
        <string>https://sender.potato</string>
      </value>
    </param>
    <param>
      <value>
        <string>https://destination.potato</string>
      </value>
    </param>
  </params>
</methodCall>
""".strip()

    assert expected_xml == output
