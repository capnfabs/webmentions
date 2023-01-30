import queue
import threading

from webmentions import db
from webmentions.db.models import FeedTask, Article
from webmentions.feed_queue import FeedQueue
from webmentions.scanner.feed import link_generator_from_feed, feed_from_url


def _process_feed(feed_task: FeedTask) -> None:
    # TODO(tech debt): move this to a package where it belongs, this is business logic, not queue
    #  logic
    print(f'Checking {feed_task.feed_url}, we checked it last on {feed_task.last_scan_completed}')

    feed = feed_from_url(feed_task.feed_url)
    assert feed
    articles = list(link_generator_from_feed(feed))
    all_article_urls = [article.absolute_url for article in articles]
    # TODO(reliability): exclude articles that are older than feed.last_reported_update_time
    with db.db_session() as session:
        # exclude articles that we've seen before
        seen_articles = session.query(Article.url).filter(
            Article.url.in_(
                all_article_urls
            )
        ).all()
        seen_articles = set(a for a, in seen_articles)
        retain_articles = [
            article for article in articles
            if article.absolute_url not in seen_articles
        ]

        articles_orm = [Article(url=a.absolute_url, feed_guid=a.guid) for a in retain_articles]
        session.add_all(articles_orm)
        session.flush()
        article_ids = [article.id for article in articles_orm]
    print(article_ids)


def _queue_thread(feed_queue: queue.Queue) -> None:
    while True:
        feed = feed_queue.get()
        # 'None' is our exit sentinel
        if feed is None:
            print('Queue is closed')
            return

        _process_feed(feed)


class InProcessQueue(FeedQueue):
    def __init__(self) -> None:
        _queue: queue.Queue = queue.Queue()
        self._queue = _queue
        # Should I switch to multiprocessing because the GIL is going to be awful? I think this
        # is mostly IO bound so probably don't need to sweat it yet.
        self._thread = threading.Thread(target=_queue_thread, args=(_queue,))
        self._thread.start()

    def close(self) -> None:
        # This is an exit sentinel for the queue processor, which should automatically terminate
        # the thread too.
        self._queue.put(None)
        self._thread.join()

    def enqueue_feed(self, feed: FeedTask) -> None:
        self._queue.put(feed)
