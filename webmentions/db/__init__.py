import contextlib
from typing import Generator, Optional, Sequence, Any

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from webmentions import config

# Note that this is lazy-inited
_MEMORY_DB = "sqlite+pysqlite:///:memory:"
engine = create_engine("sqlite+pysqlite:///local.db", echo=config.ECHO_SQL)


def maybe_init_db() -> None:
    from webmentions.db.models import Base
    Base.metadata.create_all(engine)


_READONLY_SESSION_EXCEPTION = Exception(
    "This is a readonly session, stop modifying things please; if you want to modify records then expunge them from the session."
)


@contextlib.contextmanager
def readonly_session() -> Generator[Session, None, None]:
    session = Session(engine)

    def patched_flush(objects: Optional[Sequence[Any]] = None) -> None:
        if session._is_clean():
            return
        else:
            # This is not super helpful, would be better if it included info about what things were being flushed
            raise _READONLY_SESSION_EXCEPTION

    session.flush = patched_flush  # type: ignore

    try:
        yield session
        if not session._is_clean():
            raise _READONLY_SESSION_EXCEPTION
    finally:
        # prevent a handful of idiosyncratic bugs where we could be opening DB transactions
        # without realising it.
        session.rollback()
        session.close()


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
