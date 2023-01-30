import contextlib
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from webmentions import config

# Note that this is lazy-inited
_MEMORY_DB = "sqlite+pysqlite:///:memory:"
engine = create_engine("sqlite+pysqlite:///local.db", echo=config.ECHO_SQL)


def maybe_init_db() -> None:
    from webmentions.db.models import Base
    Base.metadata.create_all(engine)


@contextlib.contextmanager
def db_session() -> Generator[Session, None, None]:
    session = Session(engine)
    try:
        yield session
        session.commit()
    except BaseException:
        # ok to catch BaseException because we're re-raising, just using this for cleanup on failure
        session.rollback()
        raise
    finally:
        # prevent a handful of idiosyncratic bugs where we could be opening DB transactions
        # without realising it.
        session.close()
