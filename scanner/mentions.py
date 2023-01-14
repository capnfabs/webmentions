import typing
from typing import NamedTuple, Optional

import bs4
import requests

import config


class MentionCapabilities(NamedTuple):
    webmention_url: Optional[str]
    pingback_url: Optional[str]


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


def fetch_page_check_mention_capabilities(url: str) -> MentionCapabilities:
    # TODO: warn that this is a page we couldn't load if we can't load it
    try:
        # Note that this follows redirects by default
        # See https://requests.readthedocs.io/en/latest/user/quickstart/#redirection-and-history
        r = requests.get(url, headers={'User-Agent': config.USER_AGENT})
        if not r.ok:
            print('not ok:', r.status_code, r.text[:1000])
            return MentionCapabilities()
    except IOError as e:
        print('not ok:', e)
        return MentionCapabilities()

    assert r.ok
    # TODO: make this lazy-parsing so that we don't load it unless we need it
    html = bs4.BeautifulSoup(r.text, features='lxml')
    webmention_link = _resolve_webmention_url(r.links, html)

    return MentionCapabilities(
        webmention_url=webmention_link,
        pingback_url=None,
    )
