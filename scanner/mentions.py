import typing
from typing import NamedTuple, Optional

import bs4
import requests

import config
import util


class MentionCapabilities(NamedTuple):
    webmention_url: Optional[str]
    pingback_url: Optional[str]


NO_CAPABILITIES = MentionCapabilities(webmention_url=None, pingback_url=None)


def _resolve_webmention_url(
        response_links: typing.Dict[str, typing.Dict[str, str]],
        response_html: bs4.BeautifulSoup,
) -> Optional[str]:
    """Return value may be a relative link, you should canonicalize it"""
    webmention_header = response_links.get('webmention')
    if webmention_header:
        webmention_url = webmention_header.get('url')
        if webmention_url:
            return webmention_url

    webmention_link = response_html.find(['link', 'a'], attrs={'rel': 'webmention'})
    # print(html.prettify())
    # href not present = invalid, href present but blank = valid and self
    if webmention_link and webmention_link.has_attr('href'):
        return webmention_link['href']

    return None


def _resolve_pingback_url(response_headers: typing.Dict[str, str], response_html: bs4.BeautifulSoup) -> Optional[str]:
    # absolute link by definition
    header_url = response_headers.get('X-Pingback')
    if header_url:
        assert util.is_absolute_link(header_url)

    # wtf the spec here is _draconian_ and also requires the parsing of HTML with regex.
    # I will ignore it for simplicity
    # http://www.hixie.ch/specs/pingback/pingback
    # TODO: make this spec-compliant
    html_link_element = response_html.find(['link'], attrs={'rel': 'pingback'})
    if html_link_element and html_link_element.has_attr('href'):
        return html_link_element['href']

    return None


def fetch_page_check_mention_capabilities(url: str) -> MentionCapabilities:
    # TODO: warn that this is a page we couldn't load if we can't load it
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
    # TODO: make this lazy-parsing so that we don't load it unless we need it
    html = bs4.BeautifulSoup(r.text, features='lxml')
    webmention_link = _resolve_webmention_url(r.links, html)
    pingback_link = _resolve_pingback_url(r.headers, html)

    return MentionCapabilities(
        webmention_url=webmention_link,
        pingback_url=pingback_link,
    )
