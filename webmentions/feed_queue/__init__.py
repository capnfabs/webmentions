from typing import Protocol

from webmentions.db.models import FeedTask


class FeedQueue(Protocol):
    def enqueue_feed(self, feed: FeedTask) -> None: ...

    def close(self) -> None: ...
