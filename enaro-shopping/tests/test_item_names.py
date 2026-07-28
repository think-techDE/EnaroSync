"""Tests for shopping-list display names."""

from __future__ import annotations

import importlib.util
from pathlib import Path

MODULE_PATH = (
    Path(__file__).parents[1]
    / "custom_components"
    / "enaro_shopping"
    / "item_names.py"
)
SPEC = importlib.util.spec_from_file_location("enaro_item_names", MODULE_PATH)
assert SPEC is not None
assert SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
format_shopping_item_name = MODULE.format_shopping_item_name


def test_capitalizes_fully_lowercase_item_name() -> None:
    assert format_shopping_item_name("milch") == "Milch"
    assert format_shopping_item_name("rote pesto") == "Rote pesto"
    assert (
        format_shopping_item_name("300g frischer spinat")
        == "300g Frischer spinat"
    )
    assert format_shopping_item_name("\u00f6l") == "\u00d6l"


def test_preserves_deliberate_casing() -> None:
    assert format_shopping_item_name("iPhone Kabel") == "iPhone Kabel"
    assert format_shopping_item_name("Coca-Cola") == "Coca-Cola"
    assert format_shopping_item_name("TK Gem\u00fcse") == "TK Gem\u00fcse"


def test_cleans_whitespace_without_changing_non_letter_input() -> None:
    assert format_shopping_item_name("  rote   pesto  ") == "Rote pesto"
    assert format_shopping_item_name("  2 x  ") == "2 x"
    assert format_shopping_item_name("123") == "123"
