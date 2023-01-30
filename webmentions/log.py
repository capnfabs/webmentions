import functools
import logging
import typing


class Logger(typing.Protocol):
    """Wrapper around logging.getLogger. Retrieve with log.get().

    The whole point of this class is that you can be sloppier with kwargs for
    the format string.
    """
    def debug(self, message: str, **kwargs: typing.Any) -> None: ...
    def info(self, message: str, **kwargs: typing.Any) -> None: ...
    def warning(self, message: str, **kwargs: typing.Any) -> None: ...
    def error(self, message: str, **kwargs: typing.Any) -> None: ...


class _LoggerImpl(Logger):
    def __init__(self, logger: logging.Logger) -> None:
        super().__init__()
        self.logger = logger

    def debug(self, message: str, **kwargs: typing.Any) -> None:
        self.log(logging.DEBUG, message, **kwargs)

    def info(self, message: str, **kwargs: typing.Any) -> None:
        self.log(logging.INFO, message, **kwargs)

    def warning(self, message: str, **kwargs: typing.Any) -> None:
        self.log(logging.WARNING, message, **kwargs)

    def error(self, message: str, **kwargs: typing.Any) -> None:
        self.log(logging.ERROR, message, **kwargs)

    def log(self, level: int, message: str, **kwargs: typing.Any) -> None:
        if kwargs:
            self.logger.log(level, message, kwargs)
        else:
            self.logger.log(level, message)


@functools.lru_cache(maxsize=None)
def get(name: str) -> Logger:
    return _LoggerImpl(logging.getLogger(name))
