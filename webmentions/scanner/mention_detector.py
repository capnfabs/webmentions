from typing import NamedTuple, Optional

import requests

from webmentions import config, util
from webmentions.util.bs4_utils import tag
from webmentions.util.request_utils import WrappedResponse


class MentionCapabilities(NamedTuple):
    webmention_url: Optional[str]
    pingback_url: Optional[str]


NO_CAPABILITIES = MentionCapabilities(webmention_url=None, pingback_url=None)


def _resolve_webmention_url(response: WrappedResponse) -> Optional[str]:
    webmention_header = response.links.get('webmention')
    if webmention_header:
        webmention_url = webmention_header.get('url')
        if webmention_url:
            return response.resolve_url(webmention_url)
    else:
        # It's legal to pass space-separated things in the `link rel` attribute, but requests doesn't parse this
        # correctly, so as a lower-performance workaround we iterate through each of the rel headers.
        for k, v in response.links.items():
            if 'webmention' in k.split():
                return response.resolve_url(v.get('url'))

    # TODO(spec): theoretically this only applies if the Content-Type is html
    webmention_links = response.parsed_html.find_all(['link', 'a'], attrs={'rel': 'webmention'})
    # href not present = invalid, href present but blank = valid and self
    for maybe_link in webmention_links:
        if maybe_link.has_attr('href'):
            # The URL is relative, so we've gotta make it absolute
            return response.resolve_url(maybe_link['href'])

    return None


def _resolve_pingback_url(response: WrappedResponse) -> Optional[str]:
    # absolute link by definition
    header_url = response.headers.get('X-Pingback')
    if header_url:
        assert util.url.is_absolute_link(header_url)
        return header_url

    # wtf the spec here is _draconian_ and also requires the parsing of HTML with regex.
    # I will ignore it for simplicity
    # http://www.hixie.ch/specs/pingback/pingback
    # TODO(spec): make this spec-compliant
    html_link_element = response.parsed_html.find(['link'], attrs={'rel': 'pingback'})
    html_link_element = tag(html_link_element)
    if html_link_element:
        hrefs = html_link_element.get_attribute_list('href')
        if hrefs:
            # could be specified multiple times, pick the first
            return hrefs[0]

    return None


def fetch_page_check_mention_capabilities(url: str) -> MentionCapabilities:
    # TODO(ux): warn that this is a page we couldn't load if we can't load it
    try:
        # Note that this follows redirects by default
        # See https://requests.readthedocs.io/en/latest/user/quickstart/#redirection-and-history
        r = requests.get(url, headers={'User-Agent': config.USER_AGENT})
        if not r.ok:
            print('not ok:', r.status_code, r.text[:1000])
            return NO_CAPABILITIES
    except IOError as e:
        print('not ok:', e)
        return NO_CAPABILITIES

    assert r.ok

    response = WrappedResponse(r)
    webmention_link = _resolve_webmention_url(response)
    pingback_link = _resolve_pingback_url(response)

    return MentionCapabilities(
        webmention_url=webmention_link,
        pingback_url=pingback_link,
    )
