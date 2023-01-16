from typing import NamedTuple

import requests

from scanner.mention_detector import MentionCapabilities


class MentionCandidate(NamedTuple):
    # absolute
    mentioner_url: str
    # absolute
    mentioned_url: str
    capabilities: MentionCapabilities


def send_mention(mention_candidate: MentionCandidate) -> None:
    data = {
        'source': mention_candidate.mentioner_url,
        'target': mention_candidate.mentioned_url,
    }
    # Pretty sure this is form-encoded by default
    # TODO(reliability): timeouts etc
    # - https://docs.gitlab.com/ee/security/webhooks.html

    webmention_url = mention_candidate.capabilities.webmention_url
    assert webmention_url
    r = requests.post(webmention_url, data=data)
    # according to spec, can return a 202 or 201
    # https://www.w3.org/TR/webmention/#sender-notifies-receiver
    # product idea: could maybe eventually use 201s as 'read receipts'
    # TODO(ux): handle not-ok, report it back to the user.
    assert r.ok
