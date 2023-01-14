import argparse
from typing import Iterable, NamedTuple
from urllib import parse

import bs4
import requests


class Link(NamedTuple):
    title: str
    url: str


def is_absolute_link(url: str) -> bool:
    return parse.urlparse(url).netloc is not None


def is_only_fragment(url: str) -> bool:
    *stuff, fragment = parse.urlparse(url)
    return bool(not any(s for s in stuff) and fragment)


def link_generator_from_rss(xml: bs4.BeautifulSoup) -> Iterable[Link]:
    for item in xml.find_all('item'):
        title = item.find('title').text
        link = item.find('link').text
        yield Link(title=title, url=link)


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


# TODO change to a real link
def parse_page_find_more_links(page_link: Link) -> Iterable[str]:
    assert is_absolute_link(page_link.url)
    parsed_page_link_netloc = parse.urlparse(page_link.url).netloc
    r = requests.get(page_link.url)
    assert r.ok
    html = bs4.BeautifulSoup(r.text, features="lxml")
    article, = html.find_all(attrs={'itemtype': "https://schema.org/Article"})
    article_body = article.find(attrs={'itemprop': 'articleBody'})
    for link in article_body.find_all('a'):
        # TODO: filter out nofollow etc
        url = link['href']
        if is_only_fragment(url):
            # print(f'Skipping {url}, is only fragment')
            continue
        elif parse.urlparse(parse.urljoin(page_link.url, url)).netloc == parsed_page_link_netloc:
            # TODO maybe also skip a hierarchy of all referred pages
            # print(f'Skipping {url}, same-origin', file=sys.stderr)
            continue

        abs_link = parse.urljoin(page_link.url, url)
        # print('outputting', abs_link)
        yield abs_link


def scan(url: str) -> None:
    r = requests.get(url)
    assert r.ok
    html = bs4.BeautifulSoup(r.text, features="lxml")
    # <link href="https://capnfabs.net/posts/index.xml" rel="alternate" title="fabian writes." type="application/rss+xml"/>
    rss_link = html.find('link', attrs={'rel': 'alternate', 'type': 'application/rss+xml'})
    assert rss_link
    resolved_url = parse.urljoin(url, rss_link['href'])
    r = requests.get(resolved_url)
    assert r.ok
    xml = bs4.BeautifulSoup(r.text, features="xml")

    for article_link in link_generator_from_rss(xml):
        # assumes that every article_link is absolute, TODO assert this
        for link in parse_page_find_more_links(article_link):
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
