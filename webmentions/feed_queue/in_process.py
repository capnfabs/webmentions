import queue
import threading

from webmentions.db.models import DiscoveryFeed
from webmentions.feed_queue import FeedQueue


def _process_feed(feed: DiscoveryFeed) -> None:
    print(
        f'Checking {feed.discovered_feed}, which was a {feed.feed_type_when_discovered} '
        f'last time we looked at it'
    )

    # articles = link_generator_from_feed(feed)


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

    def enqueue_feed(self, feed: DiscoveryFeed) -> None:
        self._queue.put(feed)
