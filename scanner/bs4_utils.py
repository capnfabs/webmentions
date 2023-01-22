import typing
from typing import Optional

import bs4


def tag(t: typing.Union[bs4.Tag | bs4.NavigableString | None]) -> Optional[bs4.Tag]:
    """
    The typing on bs4 find methods is often a little weird and returns NavigableString even when
    it's not possible that it'd return a string because you're e.g. searching by element. This
    informs the type-checker that this is a tag.
    """
    return typing.cast(Optional[bs4.Tag], t)
