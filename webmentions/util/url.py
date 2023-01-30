from urllib import parse


def is_only_fragment(url: str) -> bool:
    *stuff, fragment = parse.urlparse(url)
    return bool(not any(s for s in stuff) and fragment)


def is_absolute_link(url: str) -> bool:
    return parse.urlparse(url).netloc is not None
