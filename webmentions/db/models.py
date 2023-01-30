import base64
import datetime
import secrets
from typing import Callable, Any

from sqlalchemy import Text, DateTime, event
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from webmentions.util import now


class Base(DeclarativeBase):
    created: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False, default=now)
    updated: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False, default=now)


@event.listens_for(Base, 'before_update', propagate=True)
def before_update(_mapper: Any, _conn: Any, target: Base) -> None:
    target.updated = now()


def prefixed_id(prefix: str) -> Callable[[], str]:
    assert not prefix.endswith('_')

    def anon_method() -> str:
        return f'{prefix}_{secrets.token_urlsafe(32)}'

    return anon_method


class DiscoveryFeed(Base):
    """An article discovery feed. This is something that's specified by a user; consider this
    user-data. There's possibly multiple users all telling this service to point at the same RSS
    file, so all the 'task processing' stuff here is controlled by FeedTask. I need better
    names for both of these though. FeedTask has information about the last time we scanned
    a feed for updates.
    """
    __tablename__ = "discovery_feeds"

    # TODO(tech debt): move this into the Base class
    id: Mapped[str] = mapped_column(primary_key=True, default=prefixed_id('feed'))
    # We could theoretically end up with multiple users submitting the same thing and would need
    # to handle that somehow.
    submitted_url: Mapped[str] = mapped_column(Text, nullable=False)
    discovered_feed: Mapped[str] = mapped_column(Text, nullable=False)
    # See e.g. https://feedparser.readthedocs.io/en/latest/reference-version.html
    feed_type_when_discovered: Mapped[str] = mapped_column(Text, nullable=False)

    def __repr__(self) -> str:
        return f"DiscoveryFeed(id={self.id!r}, submitted_url={self.submitted_url!r}, " \
               f"discovered_feed={self.discovered_feed!r})"


class FeedTask(Base):
    """
    A feed that's gotta be scanned. Not 'owned' by any user. Many users could theoretically submit
    the same feed; we deactivate the scan if all users delete their submission of it.
    """
    __tablename__ = "feed_tasks"

    id: Mapped[str] = mapped_column(primary_key=True, default=prefixed_id('feedtask'))
    # We don't have a constraint for this because we'll 'tombstone' it (leave it but deactivate it)
    # if the corresponding DiscoveryFeeds are deleted
    feed_url: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    # `null` means never scanned.
    last_scan_started: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=True)
    last_scan_completed: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=True)
    # comes from the RSS file itself; used as an optimization when figuring out which articles
    # need to be processed.
    last_reported_update_time: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=True)
    # Set this to `null` to deactivate scanning (like, if the feed breaks or whatever). Set this as
    # soon as it's scheduled so that we don't start backing up more if the queue starts slowing
    # down for whatever reason.
    next_scan: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=True)


class Article(Base):
    __tablename__ = "articles"

    id: Mapped[str] = mapped_column(primary_key=True, default=prefixed_id('article'))
    # unique per feed, not globally, might not be set because RSS is janky
    feed_guid: Mapped[str] = mapped_column(Text, nullable=True)
    # unique globally
    url: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    page_scan_completed_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=True)
    notifications_completed_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=True)