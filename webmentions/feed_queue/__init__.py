from typing import Protocol

from webmentions.db.models import DiscoveryFeed


class FeedQueue(Protocol):
    def enqueue_feed(self, feed: DiscoveryFeed) -> None: ...

    def close(self) -> None: ...
