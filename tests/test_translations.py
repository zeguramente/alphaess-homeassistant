"""Tests for the translation files of the Alpha ESS integration."""

import json
from pathlib import Path
from typing import Any

_INTEGRATION_DIR = Path(__file__).parent.parent / "custom_components" / "alpha_ess"


def _load_json(relative_path: str) -> Any:
    return json.loads((_INTEGRATION_DIR / relative_path).read_text())


def _collect_keys(translations: dict[str, Any], prefix: str = "") -> set[str]:
    keys: set[str] = set()
    for key, value in translations.items():
        path = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            keys |= _collect_keys(value, path)
        else:
            keys.add(path)
    return keys


def test_english_translation_matches_strings() -> None:
    """Test that translations/en.json is an exact copy of strings.json."""
    assert _load_json("translations/en.json") == _load_json("strings.json")


def test_german_translation_is_complete() -> None:
    """Test that translations/de.json translates every key of strings.json."""
    english_keys = _collect_keys(_load_json("strings.json"))
    german_keys = _collect_keys(_load_json("translations/de.json"))

    assert english_keys - german_keys == set()
