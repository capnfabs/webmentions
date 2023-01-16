import bs4
import requests


class WrappedResponse(requests.Response):
    def __init__(self, response: requests.Response) -> None: ...

    @property
    def parsed_html(self) -> bs4.BeautifulSoup: ...

    def resolve_url(self, url: str) -> str: ...

    _response: requests.Response


def extra_spooky_monkey_patch_to_block_local_traffic() -> None: ...
