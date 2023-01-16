import argparse
from typing import Iterable, NamedTuple
from urllib import parse

import bs4
import requests

from scanner.feed import scan_site_for_feed, link_generator_from_feed, RssItem
from scanner.mention_detector import fetch_page_check_mention_capabilities
from scanner.request_utils import WrappedResponse, extra_spooky_monkey_patch_for_socket_security
from util import is_only_fragment


class Link(NamedTuple):
    title: str
    url: str


def parse_page_find_links(page_link: RssItem) -> Iterable[str]:
    parsed_page_link_netloc = parse.urlparse(page_link.absolute_url).netloc
    r = requests.get(page_link.absolute_url)
    assert r.ok
    r = WrappedResponse(r)
    html = bs4.BeautifulSoup(r.text, features="lxml")
    article, = html.find_all(attrs={'itemtype': "https://schema.org/Article"})
    article_body = article.find(attrs={'itemprop': 'articleBody'})
    for link in article_body.find_all('a'):
        # TODO: filter out nofollow etc
        # TODO: maybe include images?
        url = link.get('href')
        if not url:
            # Can't work with links that don't have an HREF
            continue
        if is_only_fragment(url):
            # print(f'Skipping {url}, is only fragment')
            continue
        abs_link = r.resolve_url(url)
        parsed_abs_link = parse.urlparse(abs_link)
        if parsed_abs_link.scheme not in ('http', 'https'):
            continue
        # TODO: maybe move this same-host check to WrappedRequest?
        if parsed_abs_link.netloc == parsed_page_link_netloc:
            # print(f'Skipping {url}, same-origin', file=sys.stderr)
            continue

        yield abs_link


def scan(url: str) -> None:
    feed = scan_site_for_feed(url)
    for article_link in link_generator_from_feed(feed):
        for link in parse_page_find_links(article_link):
            capabilities = fetch_page_check_mention_capabilities(link)
            webmention_link = capabilities.webmention_url
            pingback_link = capabilities.pingback_url
            if webmention_link is not None:
                print(f'🥕 Found a webmention for {link}! -> "{webmention_link}"')
            if pingback_link is not None:
                print(f'🥬 Found a pingback for {link}! -> "{pingback_link}"')

            if webmention_link is None and pingback_link is None:
                print(f'😢 Nothing for {link}.')


def main() -> None:
    extra_spooky_monkey_patch_for_socket_security()

    parser = argparse.ArgumentParser(
        prog='Scanner',
        description='What the program does',
        epilog='Text at the bottom of help')
    parser.add_argument('--url', required=True)
    args = parser.parse_args()

    scan(args.url)


if __name__ == '__main__':
    main()
