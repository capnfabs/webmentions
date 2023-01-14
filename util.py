from urllib import parse


def is_absolute_link(url: str) -> bool:
    return parse.urlparse(url).netloc is not None
