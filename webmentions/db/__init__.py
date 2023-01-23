import contextlib
from typing import Iterable, Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

# Note that this is lazy-inited
# TODO(security): turn off echo
_MEMORY_DB = "sqlite+pysqlite:///:memory:"
engine = create_engine("sqlite+pysqlite:///local.db", echo=True)


def maybe_init_db() -> None:
    from webmentions.db.models import Base
    Base.metadata.create_all(engine)


@contextlib.contextmanager
def db_session() -> Iterator[Session]:
    session = Session(engine)
    try:
        yield session
        session.commit()
    except BaseException:
        # ok to catch BaseException because we're re-raising, just using this for cleanup on failure
        session.rollback()
        raise
