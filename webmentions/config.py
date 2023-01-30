import contextlib
import threading
from typing import Generator, Any

USER_AGENT = 'HECK YEAH Webmentions v0.0.1'
ECHO_SQL = False

class SpookyThreadLocalRegistry(threading.local):
    def __init__(self) -> None:
        super().__init__()
        self.unsafe_requests = False

    @contextlib.contextmanager
    def enter_config(self, **kwargs: Any) -> Generator[None, None, None]:
        assert len(kwargs) == 1
        (key, val), = kwargs.items()
        old_value = self.__dict__[key]
        self.__dict__[key] = val
        try:
            yield
        finally:
            self.__dict__[key] = old_value

    @contextlib.contextmanager
    def allow_local_addresses(self) -> Generator[None, None, None]:
        with self.enter_config(unsafe_requests=True):
            yield


spooky = SpookyThreadLocalRegistry()
