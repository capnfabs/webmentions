# TODO(ux): make these somehow convertible into errors with details in CLI / web

class FeedDiscoveryException(Exception):
    pass


class NoFeedException(FeedDiscoveryException):
    pass

    def __init__(self, url: str) -> None:
        super().__init__(f"Couldn't find feed for URL '{url}'")


class RequestError(Exception):
    """Errors re: communication with an external service"""
    pass


class TransientError(RequestError):
    """Indicates that a retry might work."""


class PermanentError(RequestError):
    """Indicates that a retry definitely won't work."""
