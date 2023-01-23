import datetime
import enum
import secrets
from typing import Callable, Any

from sqlalchemy import Text, DateTime, event, types
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
    """An article discovery feed"""
    __tablename__ = "discovery_feeds"

    # TODO(tech debt): maybe move this into the Base class
    id: Mapped[str] = mapped_column(primary_key=True, default=prefixed_id('feed'))
    submitted_url: Mapped[str] = mapped_column(Text, nullable=False)
    discovered_feed: Mapped[str] = mapped_column(Text, nullable=False)
    # See e.g. https://feedparser.readthedocs.io/en/latest/reference-version.html
    feed_type_when_discovered: Mapped[str] = mapped_column(Text, nullable=False)

    def __repr__(self) -> str:
        return f"DiscoveryFeed(id={self.id!r}, submitted_url={self.submitted_url!r}, " \
               f"discovered_feed={self.discovered_feed!r})"
