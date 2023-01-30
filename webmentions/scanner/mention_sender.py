from typing import NamedTuple, Optional, NoReturn

import bs4
import requests
from lxml import etree

from webmentions.scanner import request_utils
from webmentions.scanner.bs4_utils import tag
from webmentions.scanner.mention_detector import MentionCapabilities
from webmentions import log

_log = log.get(__name__)

class MentionCandidate(NamedTuple):
    # absolute
    mentioner_url: str
    # absolute
    mentioned_url: str
    capabilities: MentionCapabilities


def _send_webmention(mention_candidate: MentionCandidate) -> None:
    webmention_url = mention_candidate.capabilities.webmention_url
    assert webmention_url

    data = {
        'source': mention_candidate.mentioner_url,
        'target': mention_candidate.mentioned_url,
    }
    # Pretty sure this is form-encoded by default
    # TODO(reliability): timeouts etc
    # - https://docs.gitlab.com/ee/security/webhooks.html

    # TODO(reliability): set user agent?
    r = requests.post(webmention_url, data=data)
    # according to spec, can return a 202 or 201
    # https://www.w3.org/TR/webmention/#sender-notifies-receiver
    # product idea: could maybe eventually use 201s as 'read receipts'
    # TODO(ux): handle not-ok, report it back to the user.
    assert r.ok


def send_mention(mention_candidate: MentionCandidate) -> None:
    if mention_candidate.capabilities.webmention_url:
        _send_webmention(mention_candidate)
    elif mention_candidate.capabilities.pingback_url:
        _send_pingback(mention_candidate)


def _send_pingback(mention_candidate: MentionCandidate) -> None:
    pingback_url = mention_candidate.capabilities.pingback_url
    assert pingback_url

    xml = _build_pingback_xml(mention_candidate)
    # TODO(reliability): set user agent?
    r = requests.post(pingback_url, data=xml, headers={'Content-Type': 'text/xml'})

    # TODO(ux): handle not-ok, report it back to the user.
    assert r.ok
    r = request_utils.WrappedResponse(r)
    fault_struct = r.parsed_xml.select('methodResponse>fault>value>struct')
    if fault_struct:
        # there should be at most one fault_struct
        _handle_fault(fault_struct[0])

    _log.info(f"Sent pingback successfully.")

    # optional return value, used for debug
    result = r.parsed_xml.select('methodResponse>params>param:first-child>value>string')
    if result:
        result_text = result[0].text
        if result_text:
            _log.info(f"Got pingback response: {result_text:1000}")


def _handle_fault(fault_struct: bs4.Tag) -> NoReturn:
    members = fault_struct.find_all('member')
    if not members:
        raise INDETERMINATE_ERROR

    def member_matches(member: bs4.Tag, name: str) -> bool:
        member_name = member.find('name')
        return bool(member_name and member_name.text == name)

    fault_code = next(member for member in members if member_matches(member, 'faultCode'))
    fault_string = next(member for member in members if member_matches(member, 'faultString'))

    def _safe_navigate(member: Optional[bs4.Tag], *path: str) -> Optional[str]:
        """Grabs a value"""
        for p in path:
            if not member:
                return None
            member = tag(member.find(p))

        if not member:
            return None

        return member.text

    fault_code = _safe_navigate(fault_code, 'value', 'int')
    try:
        fault_code = int(fault_code)
    except ValueError:
        fault_code = None
    fault_string = _safe_navigate(fault_string, 'value', 'string')
    if fault_code is not None and fault_string is not None:
        # this is log.info because it's somewhat ordinary operation for our service even though it's
        # probably bad for the user and we should handle it upstream.
        _log.info(f'Got pingback fault: {fault_code} / {fault_string[:1000]}')
        raise RemoteError(fault_code, fault_string)
    else:
        _log.info(f'Got malformed pingback fault response: {fault_struct.prettify()}')
        raise INDETERMINATE_ERROR


class RemoteError(Exception):
    def __init__(self, code: int, message: str) -> None:
        super().__init__(f'{code}: {message}')

        # Now for your custom code...
        self.code = code
        self.message = message


INDETERMINATE_ERROR = RemoteError(code=-1, message='Got a malformed xml document from remote host')


def _build_pingback_xml(mention_candidate: MentionCandidate) -> str:
    """Totally fine for this to return a string because the document will
    probably be tiny.
    """
    source_uri = mention_candidate.mentioner_url
    target_uri = mention_candidate.mentioned_url

    method_call = etree.Element('methodCall')
    method_name = etree.Element('methodName')
    method_name.text = 'pingback.ping'
    method_call.append(method_name)

    params = etree.Element('params')
    method_call.append(params)
    source_param = _build_param(source_uri)
    params.append(source_param)
    target_param = _build_param(target_uri)
    params.append(target_param)
    xml_tree = etree.ElementTree(method_call)
    return etree.tostring(
        xml_tree, pretty_print=True, xml_declaration=True, encoding="utf-8"
    ).decode('utf-8')


def _build_param(value_abs_url: str) -> etree._Element:
    source_param = etree.Element('param')
    value = etree.Element('value')
    str_value = etree.Element('string')
    str_value.text = value_abs_url
    value.append(str_value)
    source_param.append(value)
    return source_param
