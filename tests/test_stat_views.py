"""Tests for safe per-game presentation of season projections."""

import pandas as pd
import pytest

from nba_fantasy_lab.stat_views import PER_GAME_LABELS, convert_to_per_game


def test_converts_totals_without_changing_input():
    original = pd.DataFrame({
        "Mecze": [80], "PTS": [1600.0], "REB": [480.0],
        "AST": [640.0], "STL": [120.0], "BLK": [40.0],
        "3PM": [200.0], "TO": [240.0],
    })
    output = convert_to_per_game(original)
    assert output.loc[0, "PTS"] == 20.0
    assert output.loc[0, "REB"] == 6.0
    assert output.loc[0, "AST"] == 8.0
    assert output.loc[0, "STL"] == 1.5
    assert output.loc[0, "BLK"] == 0.5
    assert output.loc[0, "3PM"] == 2.5
    assert output.loc[0, "TO"] == 3.0
    assert original.loc[0, "PTS"] == 1600.0
    assert output.loc[0, "Mecze"] == 80


def test_missing_and_zero_games_produce_missing_averages():
    frame = pd.DataFrame({
        "Mecze": [None, 0, -2, 20],
        "PTS": [120.0, 120.0, 120.0, None],
    })
    result = convert_to_per_game(frame)
    assert result["PTS"].isna().all()


def test_percentages_and_team_wins_are_not_modified():
    frame = pd.DataFrame({
        "Mecze": [40], "PTS": [800.0],
        "FG%": [49.5], "FT%": [82.3], "TW": [None],
        "Zawodnik": ["Demo Player"],
    })
    result = convert_to_per_game(frame)
    assert result.loc[0, "FG%"] == 49.5
    assert result.loc[0, "FT%"] == 82.3
    assert pd.isna(result.loc[0, "TW"])
    assert result.loc[0, "Zawodnik"] == "Demo Player"


def test_sorting_uses_per_game_values_not_season_totals():
    frame = pd.DataFrame({
        "Zawodnik": ["A", "B"],
        "Mecze": [40, 80],
        "PTS": [800.0, 1200.0],
    })
    assert frame.sort_values("PTS", ascending=False).iloc[0]["Zawodnik"] == "B"
    per_game = convert_to_per_game(frame)
    assert per_game.sort_values("PTS", ascending=False).iloc[0]["Zawodnik"] == "A"


def test_column_labels_and_missing_games_column():
    assert PER_GAME_LABELS["PTS"] == "PPG"
    assert PER_GAME_LABELS["3PM"] == "3PM/G"
    assert "FG%" not in PER_GAME_LABELS
    with pytest.raises(ValueError, match="Mecze"):
        convert_to_per_game(pd.DataFrame({"PTS": [10.0]}))
