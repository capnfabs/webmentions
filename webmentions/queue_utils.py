import queue
import threading
from typing import Callable, Generic, Protocol, TypeVar, Any
from webmentions import log

T = TypeVar('T', contravariant=True)

_log = log.get(__name__)

class TaskQueue(Protocol, Generic[T]):
    def enqueue(self, item: T) -> None: ...

    def close(self) -> None: ...


def _make_sentinel() -> Any:
    class SpookyAnonymousClass:
        pass
    return SpookyAnonymousClass()

_EXIT_SENTINEL = _make_sentinel


class InProcessQueue(TaskQueue[T], Generic[T]):

    def _queue_thread(self, item_queue: queue.Queue, item_processor: Callable[[T], None]) -> None:
        _log.info('Queue %(queue)s starting', queue=self)
        while True:
            item = item_queue.get()

            if item is _EXIT_SENTINEL:
                break

            # TODO(reliability): should we handle errors gracefully here?
            item_processor(item)

        _log.info('Queue %(queue)s exiting normally', queue=self)

    def __init__(self, item_processor: Callable[[T], None]) -> None:
        _queue: queue.Queue = queue.Queue()
        self._queue = _queue

        # Should I switch to multiprocessing because the GIL is going to be awful? I think this
        # is mostly IO bound so probably don't need to sweat it yet.
        self._thread = threading.Thread(target=self._queue_thread, args=(_queue, item_processor))
        self._thread.start()

    def close(self) -> None:
        # Putting this on the queue will terminate the thread, so the join will succeed once all
        # items have been processed. I think.
        self._queue.put(_EXIT_SENTINEL)
        self._thread.join()

    def enqueue(self, item: T) -> None:
        self._queue.put(item)
