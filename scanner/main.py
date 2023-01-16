import argparse
from typing import Iterable, NamedTuple, Optional
from urllib import parse

import bs4
import requests

from scanner.feed import scan_site_for_feed, link_generator_from_feed, RssItem
from scanner.mention_detector import fetch_page_check_mention_capabilities, NO_CAPABILITIES
from scanner.mention_sender import send_mention, MentionCandidate
from scanner.request_utils import WrappedResponse, extra_spooky_monkey_patch_to_block_local_traffic
from util import is_only_fragment


class Link(NamedTuple):
    title: str
    url: str


def _find_article_schema_org(html: bs4.BeautifulSoup) -> Optional[bs4.Tag]:
    schema_org_article = html.find_all(attrs={'itemtype': "https://schema.org/Article"})
    if not schema_org_article:
        return None
    article_body = schema_org_article.find(attrs={'itemprop': 'articleBody'})
    return article_body


def _find_article_semantic_html(html: bs4.BeautifulSoup) -> Optional[bs4.Tag]:
    all_articles = html.find_all('article')
    print(all_articles)
    if len(all_articles) == 1:
        return all_articles[0]


def find_article(html: bs4.BeautifulSoup) -> Optional[bs4.Tag]:
    return _find_article_schema_org(html) or _find_article_semantic_html(html)


def parse_page_find_links(page_link: RssItem) -> Iterable[str]:
    parsed_page_link_netloc = parse.urlparse(page_link.absolute_url).netloc
    r = requests.get(page_link.absolute_url)
    assert r.ok
    r = WrappedResponse(r)
    html = bs4.BeautifulSoup(r.text, features="lxml")
    article_body = find_article(html)
    if article_body is None:
        print("Couldn't resolve article")
        return

    for link in article_body.find_all('a'):
        # TODO(ux): filter out nofollow etc
        # TODO(ux): maybe include images?
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


def scan(url: str, notify: bool) -> None:
    for mentionable in generate_webmention_candidates(url):
        if notify:
            send_mention(mentionable)
        else:
            webmention_link = mentionable.capabilities.webmention_url
            pingback_link = mentionable.capabilities.pingback_url
            if webmention_link is not None:
                print(f'🥕 Found a webmention for {mentionable.mentioned_url}! -> "{webmention_link}"')
            if pingback_link is not None:
                print(f'🥬 Found a pingback for {mentionable.mentioned_url}! -> "{pingback_link}"')


def generate_webmention_candidates(url: str) -> Iterable[MentionCandidate]:
    feed = scan_site_for_feed(url)
    for article_link in link_generator_from_feed(feed):
        for link in parse_page_find_links(article_link):
            capabilities = fetch_page_check_mention_capabilities(link)
            if capabilities != NO_CAPABILITIES:
                yield MentionCandidate(
                    mentioner_url=article_link,
                    mentioned_url=link,
                    capabilities=capabilities,
                )


def main() -> None:
    extra_spooky_monkey_patch_to_block_local_traffic()

    parser = argparse.ArgumentParser(
        prog='Scanner',
        description='What the program does',
        epilog='Text at the bottom of help')
    parser.add_argument('--url', required=True)
    parser.add_argument('--real', action='store_true')
    args = parser.parse_args()

    scan(args.url, args.real)


if __name__ == '__main__':
    main()
