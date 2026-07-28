"""Display-name handling for shopping-list items."""

from __future__ import annotations

import re

_WHITESPACE_PATTERN = re.compile(r"\s+")
_READABLE_WORD_START_PATTERN = re.compile(
    r"(?<!\w)([^\W\d_])(?=[^\W\d_])",
    flags=re.UNICODE,
)


def format_shopping_item_name(value: str) -> str:
    """Clean an item name and improve fully lowercase legacy input.

    Home Assistant may provide lower-case summaries, depending on the input
    method. Preserve deliberate mixed casing, but give plain lower-case names
    a readable sentence-style start.
    """
    cleaned = _WHITESPACE_PATTERN.sub(" ", value).strip()
    if not cleaned or any(character.isupper() for character in cleaned):
        return cleaned

    match = _READABLE_WORD_START_PATTERN.search(cleaned)
    if match is not None:
        index = match.start(1)
        character = match.group(1)
        return f"{cleaned[:index]}{character.upper()}{cleaned[index + 1:]}"
    return cleaned
