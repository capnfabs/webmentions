from typing import Optional, Iterable
from urllib import parse

import bs4
import requests

from webmentions import config
from webmentions.util.bs4_utils import tag
from webmentions.util.request_utils import WrappedResponse
from webmentions.util.url import is_only_fragment


def _find_article_schema_org(html: bs4.BeautifulSoup) -> Optional[bs4.Tag]:
    schema_org_article = html.find_all(attrs={'itemtype': "https://schema.org/Article"})
    if not schema_org_article or len(schema_org_article) > 1:
        return None
    article_body = tag(schema_org_article[0].find(attrs={'itemprop': 'articleBody'}))
    return article_body


def _find_article_semantic_html(html: bs4.BeautifulSoup) -> Optional[bs4.Tag]:
    all_articles = html.find_all('article')
    if len(all_articles) == 1:
        return tag(all_articles[0])

    return None


def _find_article(html: bs4.BeautifulSoup) -> Optional[bs4.Tag]:
    return _find_article_schema_org(html) or _find_article_semantic_html(html)


def parse_page_find_links(absolute_url: str) -> Iterable[str]:
    parsed_page_link_netloc = parse.urlparse(absolute_url).netloc
    with config.spooky.allow_local_addresses():
        r = requests.get(absolute_url)
    assert r.ok
    r = WrappedResponse(r)
    html = bs4.BeautifulSoup(r.text, features="lxml")
    article_body = _find_article(html)
    if article_body is None:
        # TODO(ux): report this probably
        print("Couldn't resolve article")
        return

    for link in article_body.find_all('a'):
        # TODO(ux): filter out nofollow etc
        # TODO(ux): maybe include images?
        # TODO:(reliability): maybe cap these to url MAX_LENGTH?
        #  See eg. https://www.baeldung.com/cs/max-url-length but there's no actual spec'd limit
        #  AFAICT
        url = link.get('href')
        if not url:
            # Can't work with links that don't have an HREF
            continue
        if is_only_fragment(url):
            continue
        abs_link = r.resolve_url(url)
        parsed_abs_link = parse.urlparse(abs_link)
        if parsed_abs_link.scheme not in ('http', 'https'):
            continue
        if parsed_abs_link.netloc == parsed_page_link_netloc:
            continue

        yield abs_link
