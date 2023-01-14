import io
from typing import Iterable, NamedTuple, Optional
from urllib import parse

import bs4
import feedparser  # type: ignore
import requests

import util


class Feed(NamedTuple):
    absolute_url: str
    content: feedparser.FeedParserDict


class RssItem(NamedTuple):
    title: str
    absolute_url: str


def link_generator_from_feed(feed: Feed) -> Iterable[RssItem]:
    for item in feed.content.entries:
        # from RSS spec: link is optional
        link = item.get('link')
        if not link:
            # Doesn't make sense to handle this if there's no link (we're gonna send a mention based on this link).
            continue
        if not util.is_absolute_link(link):
            # We can probably handle these gracefully eventually, but not yet.
            continue

        # from RSS spec: title is optional if description is set
        # https://www.rssboard.org/rss-draft-1#element-channel-item
        title = item.get('title', link)

        assert util.is_absolute_link(link)
        yield RssItem(title=title, absolute_url=link)


def scan_site_for_feed(url: str) -> Optional[Feed]:
    r = requests.get(url)
    assert r.ok
    html = bs4.BeautifulSoup(r.text, features="lxml")
    rss_link = html.find('link', attrs={'rel': 'alternate', 'type': 'application/rss+xml'})
    atom_link = html.find('link', attrs={'rel': 'alternate', 'type': 'application/atom+xml'})

    def fetch_feed(link_elem: Optional[bs4.element.Tag]) -> Optional[Feed]:
        if link_elem is None:
            return None

        resolved_url = parse.urljoin(url, rss_link['href'])
        r = requests.get(resolved_url)
        if not r.ok:
            # TODO: let user know, this is an error in their site or their server is borked or something
            return None

        assert util.is_absolute_link(resolved_url)
        # don't need HTML sanitisation because we're not sticking it in a website or anything
        # wrapped in BytesIO because as per docs, untrusted strings can trigger filesystem access (!?)
        # It is cursed; I do not like it one bit.
        # the docs say that you can pass a StringIO around a string, but it breaks a regex somewhere in feedparser,
        # so you have to supply a BytesIO and then pass the response headers through to maximise the chances of getting
        # the content encoding right. Gross.
        # TODO: wrap feedparser to watch out for sharp edges
        return Feed(
            absolute_url=resolved_url,
            content=feedparser.parse(io.BytesIO(r.content), response_headers=r.headers),
        )

    # rss has preference, chosen arbitrarily 🤷
    links = [rss_link, atom_link]
    candidate_feeds = (fetch_feed(link) for link in links)
    chosen_feed = next(candidate_feeds)
    if not chosen_feed:
        # TODO: alert user
        return None

    return chosen_feed
