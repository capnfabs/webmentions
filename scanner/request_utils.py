import functools
from urllib import parse

import bs4
import requests


class WrappedResponse:
    """Wraps a requests Response and adds some useful utils"""

    def __init__(self, response: requests.Response) -> None:
        self._response: requests.Response = response

    @functools.cached_property
    def parsed_html(self) -> bs4.BeautifulSoup:
        # TODO: content-type check
        return bs4.BeautifulSoup(self._response.text, features='lxml')

    def resolve_url(self, url: str) -> str:
        """Resolves a URL based on the end-URL of the response"""
        return parse.urljoin(self._response.url, url)

    def __getattr__(self, attr):
        return getattr(self._response, attr)
