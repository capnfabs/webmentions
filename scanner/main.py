import argparse
from typing import Iterable, NamedTuple
from urllib import parse

import bs4
import requests
from scanner.feed import scan_site_for_feed, link_generator_from_feed, RssItem


class Link(NamedTuple):
    title: str
    url: str


def is_only_fragment(url: str) -> bool:
    *stuff, fragment = parse.urlparse(url)
    return bool(not any(s for s in stuff) and fragment)


def fetch_page_check_webmention(url: str) -> None:
    try:
        # Note that this follows redirects by default https://requests.readthedocs.io/en/latest/user/quickstart/#redirection-and-history
        r = requests.get(url, headers={'User-Agent': 'HECK YEAH Webmentions v0.0.1'})
        if not r.ok:
            print('not ok:', r.status_code, r.text[:1000])
            return
    except IOError as e:
        print('not ok:', e)
        return

    assert r.ok
    webmention_header = r.links.get('webmention')
    if webmention_header:
        webmention_url = webmention_header.get('url')
        if webmention_url:
            print(f'🥳 Found a webmention for {url}!', webmention_url)
            return

    # <link href="http://aaronpk.example/webmention-endpoint" rel="webmention" />
    html = bs4.BeautifulSoup(r.text, features='lxml')
    webmention_link = html.find(['link', 'a'], attrs={'rel': 'webmention'})
    # print(html.prettify())
    # href not present = invalid, href present but blank = valid and self
    if webmention_link and webmention_link.has_attr('href'):
        print(f'🥳 Found a webmention for {url}!', webmention_link['href'])
    else:
        print(f'😢 No webmention for {url}.')


def parse_page_find_links(page_link: RssItem) -> Iterable[str]:
    parsed_page_link_netloc = parse.urlparse(page_link.absolute_url).netloc
    r = requests.get(page_link.absolute_url)
    assert r.ok
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
        abs_link = parse.urljoin(page_link.absolute_url, url)
        parsed_abs_link = parse.urlparse(abs_link)
        if parsed_abs_link.scheme not in ('http', 'https'):
            continue
        if parsed_abs_link.netloc == parsed_page_link_netloc:
            # print(f'Skipping {url}, same-origin', file=sys.stderr)
            continue

        # print('outputting', abs_link)
        yield abs_link


def scan(url: str) -> None:
    feed = scan_site_for_feed(url)
    for article_link in link_generator_from_feed(feed):
        # assumes that every article_link is absolute, TODO assert this
        for link in parse_page_find_links(article_link):
            fetch_page_check_webmention(link)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog='Scanner',
        description='What the program does',
        epilog='Text at the bottom of help')
    parser.add_argument('--url', required=True)
    args = parser.parse_args()
    scan(args.url)


if __name__ == '__main__':
    main()
