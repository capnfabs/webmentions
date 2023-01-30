import argparse
from typing import Iterable, Optional

from webmentions.article_queue import InProcessArticleQueue
from webmentions.notification_queue import InProcessNotificationQueue
from webmentions.util import aqueue
from webmentions import util, db, config
from webmentions.db import models, maybe_init_db
from webmentions.db.models import FeedTask
from webmentions.feed_queue.in_process import InProcessQueue
from webmentions.scanner.article_handler import parse_page_find_links
from webmentions.scanner.errors import NoFeedException
from webmentions.scanner.feed import scan_site_for_feed, link_generator_from_feed, RssItem
from webmentions.scanner.mention_detector import fetch_page_check_mention_capabilities
from webmentions.scanner.mention_sender import send_mention, MentionCandidate
from webmentions.util.aqueue import NoopQueue
from webmentions.util.request_utils import extra_spooky_monkey_patch_to_block_local_traffic
from webmentions.util.time import now


def _generate_webmention_candidates(url: str, single_page: bool) -> Iterable[MentionCandidate]:
    if single_page:
        articles: Iterable[RssItem] = [RssItem(title='single page', absolute_url=url, guid=None)]
    else:
        feed = scan_site_for_feed(url)
        if not feed:
            raise NoFeedException(url)

        articles = link_generator_from_feed(feed)

    for article_link in articles:
        print(f'checking {article_link}')

        for link in parse_page_find_links(article_link.absolute_url):
            capabilities = fetch_page_check_mention_capabilities(link)
            if capabilities:
                yield MentionCandidate(
                    mentioner_url=article_link.absolute_url,
                    mentioned_url=link,
                    capabilities=capabilities,
                )


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


def _scan_saved(notify: bool) -> None:
    if notify:
        notification_queue: aqueue.TaskQueue[str] = InProcessNotificationQueue()
    else:
        notification_queue = NoopQueue()
    article_queue: aqueue.TaskQueue[str] = InProcessArticleQueue(notification_queue)
    feed_queue: aqueue.TaskQueue[FeedTask] = InProcessQueue(article_queue.enqueue)

    try:
        # Load all saved items
        with db.db_session() as session:
            feeds = session.query(FeedTask).all()
            session.expunge_all()
        for feed in feeds:
            print(f'Checking feed {feed.feed_url}...')
            feed_queue.enqueue(feed)
    finally:
        # gotta get the order right here because some of them depend on the others
        feed_queue.close()
        article_queue.close()
        notification_queue.close()


def _register(url: str) -> None:
    assert util.url.is_absolute_link(url)

    feed = scan_site_for_feed(url)
    if not feed:
        raise NoFeedException(url)

    # TODO(ux): validate that the feed is valid, that it contains URLs etc.
    feed_model = models.DiscoveryFeed(
        submitted_url=url,
        discovered_feed=feed.absolute_url,
        feed_type_when_discovered=feed.content.version,
    )

    with db.db_session() as session:
        session.add(feed_model)
        session.flush()
        task: Optional[FeedTask] = (
            session
            .query(FeedTask)
            .filter(FeedTask.feed_url == feed.absolute_url)
            .one_or_none()
        )
        # Pretty sure there are race conditions that can cause this to fail because of
        # transaction isolation, but it's very difficult to do something about them because we
        # don't have 'on-conflict' support in SQLAlchemy ORM.
        if task:
            task.next_scan = now()
        else:
            session.add(FeedTask(feed_url=feed.absolute_url, next_scan=now()))

    print('Added feed to DB')


def _configure_logging(verbosity: int) -> None:
    import logging

    if verbosity >= 3:
        # TODO: this doesn't work right now because the db engine gets imported
        # before anything else happens
        config.ECHO_SQL = True
        logging.basicConfig(level=logging.DEBUG)
    elif verbosity == 2:
        logging.basicConfig(level=logging.DEBUG)
    elif verbosity == 1:
        logging.basicConfig(level=logging.INFO)
    else:
        logging.basicConfig()


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

    # Verbose
    parser.add_argument('--verbose', '-v', action='count', default=0)

    args = parser.parse_args()

    _configure_logging(args.verbose)

    all_mode_args = [args.site, args.page, args.register]
    count_mode_args = len([arg for arg in all_mode_args if arg])
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
