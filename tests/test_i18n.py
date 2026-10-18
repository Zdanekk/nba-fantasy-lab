"""Tests for language-neutral identifiers and bilingual UI texts."""

from string import Formatter
import sys
from types import SimpleNamespace

import pytest

from nba_fantasy_lab.i18n import (
    COLUMN_KEYS,
    LANGUAGES,
    TEXT,
    column_label,
    language_selector,
    translate,
)


def test_translations_have_matching_keys():
    assert LANGUAGES == ("pl", "en")
    assert TEXT["pl"]
    assert set(TEXT["pl"]) == set(TEXT["en"])


def test_placeholders_match_between_languages():
    for key in TEXT["pl"]:
        pl_fields = {
            field for _, field, _, _ in Formatter().parse(TEXT["pl"][key])
            if field is not None
        }
        en_fields = {
            field for _, field, _, _ in Formatter().parse(TEXT["en"][key])
            if field is not None
        }
        assert pl_fields == en_fields, key


def test_translation_values_are_nonempty():
    assert all(value.strip() for table in TEXT.values() for value in table.values())


def test_language_fallback_and_interpolation():
    assert translate("home.players", "pl") == "Zawodnicy w bazie"
    assert translate("home.players", "en") == "Players in database"
    assert translate("home.players", "invalid") == "Zawodnicy w bazie"
    assert "12" in translate("import.demo_success", "en", count=12)
    assert "11" in translate("draft.pick_saved", "pl", number=11, player="Example")
    with pytest.raises(KeyError):
        translate("nonexistent", "en")


def test_column_labels_keep_stat_abbreviations():
    assert column_label("Zawodnik", "en") == "Player"
    assert column_label("Zespół", "en") == "Team"
    assert column_label("Mecze", "en") == "Games"
    assert column_label("PTS", "en") == "PTS"
    assert column_label("FG%", "en") == "FG%"
    assert set(COLUMN_KEYS) == {"Zawodnik", "Zespół", "Pozycje", "Mecze"}


def test_draft_identifiers_are_translated_for_display_only():
    assert translate("draft.status.setup", "en") == "Setup"
    assert translate("draft.status.in_progress", "en") == "In progress"
    assert translate("draft.event.pick", "en") == "Pick"
    assert translate("draft.event.undo", "pl") == "Cofnięcie"


def test_language_preference_survives_page_navigation(monkeypatch):
    """Recreating a widget must not overwrite the non-widget language setting."""
    state = {"fantasy_language_preference": "en"}
    callbacks = []

    def mock_selectbox(_label, *, options, key, on_change, format_func):
        assert list(options) == ["pl", "en"]
        assert format_func("en").endswith("English")
        callbacks.append(on_change)
        return state[key]

    streamlit_stub = SimpleNamespace(
        session_state=state,
        sidebar=SimpleNamespace(selectbox=mock_selectbox),
    )
    monkeypatch.setitem(sys.modules, "streamlit", streamlit_stub)

    language_selector()
    assert state["_fantasy_language_widget"] == "en"

    state["_fantasy_language_widget"] = "pl"
    callbacks[-1]()
    assert state["fantasy_language_preference"] == "pl"

    state.pop("_fantasy_language_widget")
    language_selector()
    assert state["_fantasy_language_widget"] == "pl"
