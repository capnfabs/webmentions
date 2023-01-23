import functools
import ipaddress
import socket
import threading
from typing import Any
from urllib import parse

import bs4
import requests

from webmentions import config


class WrappedResponse:
    """Wraps a requests Response and adds some useful utils"""

    def __init__(self, response: requests.Response) -> None:
        self._response: requests.Response = response

    @functools.cached_property
    def parsed_html(self) -> bs4.BeautifulSoup:
        # TODO(reliability): content-type check
        return bs4.BeautifulSoup(self._response.text, features='lxml')

    @functools.cached_property
    def parsed_xml(self) -> bs4.BeautifulSoup:
        # TODO(reliability): content-type check
        return bs4.BeautifulSoup(self._response.text, features='lxml-xml')

    def resolve_url(self, url: str) -> str:
        """Resolves a URL based on the end-URL of the response"""
        return parse.urljoin(self._response.url, url)

    def __getattr__(self, attr):
        return getattr(self._response, attr)


def _init_threadlocal():
    registry = threading.local()
    registry.__dict__.setdefault('unsafe_requests', False)
    return registry

def extra_spooky_monkey_patch_to_block_local_traffic() -> None:
    """Sorry / not sorry"""
    local_getaddrinfo = socket.getaddrinfo

    def _addrinfo_represents_global_ip(addrinfo_tuple: Any) -> bool:
        (family, type, proto, canonname, sockaddr) = addrinfo_tuple
        if family not in (socket.AF_INET, socket.AF_INET6):
            # ipv4/v6 only, no shenanigans please
            return False

        # For IPv4, this is a 2-tuple with IP/port
        # For IPv6, this is a 4-tuple with IP/port/flowinfo/scope_id apparently
        ip, *_ = sockaddr
        return ipaddress.ip_address(ip).is_global

    def new_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0) -> Any:
        results = local_getaddrinfo(host, port, family=family, type=type, proto=proto, flags=flags)
        if config.spooky.unsafe_requests:
            return results
        else:
            return [r for r in results if _addrinfo_represents_global_ip(r)]

    socket.getaddrinfo = new_getaddrinfo
