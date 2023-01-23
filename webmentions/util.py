import datetime
from urllib import parse


def is_absolute_link(url: str) -> bool:
    return parse.urlparse(url).netloc is not None


def is_only_fragment(url: str) -> bool:
    *stuff, fragment = parse.urlparse(url)
    return bool(not any(s for s in stuff) and fragment)


def now() -> datetime.datetime:
    return datetime.datetime.utcnow()


HOUR = datetime.timedelta(hours=1)
DAY = datetime.timedelta(days=1)
