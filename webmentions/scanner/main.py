import argparse
from typing import Iterable, NamedTuple, Optional
from urllib import parse

import bs4
import requests

from webmentions import util, db
from webmentions.db import models, maybe_init_db
from webmentions.scanner import request_utils
from webmentions.scanner.bs4_utils import tag
from webmentions.scanner.errors import NoFeedException
from webmentions.scanner.feed import scan_site_for_feed, link_generator_from_feed, RssItem
from webmentions.scanner.mention_detector import fetch_page_check_mention_capabilities, \
    NO_CAPABILITIES
from webmentions.scanner.mention_sender import send_mention, MentionCandidate
from webmentions.scanner.request_utils import WrappedResponse, \
    extra_spooky_monkey_patch_to_block_local_traffic
from webmentions.util import is_only_fragment


class Link(NamedTuple):
    title: str
    url: str


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


def _parse_page_find_links(page_link: RssItem) -> Iterable[str]:
    parsed_page_link_netloc = parse.urlparse(page_link.absolute_url).netloc
    with request_utils.allow_local_addresses():
        r = requests.get(page_link.absolute_url)
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


def _scan(url: str, *, notify: bool, single_page: bool) -> None:
    for mentionable in _generate_webmention_candidates(url, single_page):
        if notify:
            send_mention(mentionable)
        else:
            webmention_link = mentionable.capabilities.webmention_url
            pingback_link = mentionable.capabilities.pingback_url
            if webmention_link is not None:
                print(
                    f'🥕 Found a webmention for {mentionable.mentioned_url}! -> "{webmention_link}"'
                )
            if pingback_link is not None:
                print(f'🥬 Found a pingback for {mentionable.mentioned_url}! -> "{pingback_link}"')


def _generate_webmention_candidates(url: str, single_page: bool) -> Iterable[MentionCandidate]:
    if single_page:
        articles: Iterable[RssItem] = [RssItem(title='single page', absolute_url=url)]
    else:
        feed = scan_site_for_feed(url)
        if not feed:
            raise NoFeedException(url)

        articles = link_generator_from_feed(feed)

    for article_link in articles:
        print(f'checking {article_link}')
        for link in _parse_page_find_links(article_link):
            capabilities = fetch_page_check_mention_capabilities(link)
            if capabilities != NO_CAPABILITIES:
                yield MentionCandidate(
                    mentioner_url=article_link.absolute_url,
                    mentioned_url=link,
                    capabilities=capabilities,
                )


def _scan_saved(notify: bool) -> None:
    pass


def _register(url: str) -> None:
    assert util.is_absolute_link(url)

    feed = scan_site_for_feed(url)
    if not feed:
        raise NoFeedException(url)

    # TODO: validate that the feed is valid, that it contains URLs etc.
    feed_model = models.DiscoveryFeed(
        submitted_url=url,
        discovered_feed=feed.absolute_url,
        feed_type_when_discovered=feed.content.version,
    )

    with db.db_session() as session:
        session.add(feed_model)

    print('Added feed to DB')


def main() -> None:
    extra_spooky_monkey_patch_to_block_local_traffic()
    maybe_init_db()

    parser = argparse.ArgumentParser(
        prog='Scanner',
        description='What the program does',
        epilog='Text at the bottom of help'
    )
    # scans a whole site, finds RSS feed from provided URL and does webmention discovery from there.
    # doesn't deduplicate or anything
    parser.add_argument('--site')

    # scans a single page and sends webmentions. Doesn't attempt to dedupe previously sent mentions.
    parser.add_argument('--page')

    # looks up a feed, saves it in the database. You're then able to run without any args to have
    # this scan for new webmentions targets.
    parser.add_argument('--register')

    # Actually send the webmentions. Like the opposite of a dry_run flag.
    parser.add_argument('--real', action='store_true')
    args = parser.parse_args()

    all_args = [args.site, args.page, args.register]
    count_mode_args = len([arg for arg in all_args if arg])
    if count_mode_args > 1:
        # TODO: make this user facing
        raise Exception("Only one of `site`, `page` and `register` can be supplied.")
    elif count_mode_args == 1:
        if args.site:
            _scan(args.site, notify=args.real, single_page=False)
        elif args.page:
            _scan(args.page, notify=args.real, single_page=True)
        elif args.register:
            _register(args.register)
        else:
            # should be unreachable
            assert False
    else:
        # no args, produce results for saved entries
        _scan_saved(notify=args.real)


if __name__ == '__main__':
    main()
