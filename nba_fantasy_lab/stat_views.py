"""Presentation-only conversions for projected season statistics.

Keep season totals in SQLite and in the ranking engine. Convert only a copy
of the player table for display and sorting in Streamlit.
"""

import pandas as pd


PER_GAME_LABELS = {
    "PTS": "PPG",
    "REB": "RPG",
    "AST": "APG",
    "STL": "SPG",
    "BLK": "BPG",
    "3PM": "3PM/G",
    "TO": "TO/G",
}


def convert_to_per_game(frame: pd.DataFrame) -> pd.DataFrame:
    """Convert season-count columns into per-game values without mutating input.

    Missing, zero, or negative projected games yield missing averages (NaN).
    Shooting percentages, games, and unverified Team Wins remain unchanged.
    """
    if "Mecze" not in frame.columns:
        raise ValueError("Missing required projected-games column: Mecze")

    result = frame.copy()
    games = pd.to_numeric(result["Mecze"], errors="coerce")
    games = games.where(games > 0)

    for column in PER_GAME_LABELS:
        if column in result.columns:
            totals = pd.to_numeric(result[column], errors="coerce")
            result[column] = totals / games

    return result
