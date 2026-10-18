"""Transparent season-total Z-score rankings for nine verified scoring categories.

Team Wins (TW) is intentionally excluded until ESPN rules are verified.
A missing or constant category yields no Z-score; incomplete players do not
receive a total score or a rank.
"""

from pathlib import Path

import numpy as np
import pandas as pd

from nba_fantasy_lab.database import DEFAULT_DB_PATH, get_connection

SEASON = "2026/27"

# Each category maps to the Z-score column exposed by this module.
SCORE_COLUMNS = {
    "PTS": "z_pts",
    "REB": "z_reb",
    "AST": "z_ast",
    "STL": "z_stl",
    "BLK": "z_blk",
    "3PM": "z_three_pm",
    "FG%": "z_fg_pct",
    "FT%": "z_ft_pct",
    "TO": "z_to",
}

STAT_COLUMNS = {
    "pts": "z_pts",
    "reb": "z_reb",
    "ast": "z_ast",
    "stl": "z_stl",
    "blk": "z_blk",
    "three_pm": "z_three_pm",
    "turnovers": "z_to",
}

REQUIRED_COLUMNS = {
    "player_id", "full_name", "fgm", "fga", "ftm", "fta",
    *STAT_COLUMNS,
}


def _z_score(series: pd.Series, *, lower_is_better: bool = False) -> pd.Series:
    """Calculate population Z-scores; preserve missing and constant values."""
    valid = series.dropna()
    result = pd.Series(np.nan, index=series.index, dtype="float64")
    if len(valid) < 2:
        return result

    standard_deviation = valid.std(ddof=0)
    if not np.isfinite(standard_deviation) or standard_deviation <= 1e-12:
        return result

    result = (series - valid.mean()) / standard_deviation
    return -result if lower_is_better else result


def _percentage_impact(
    frame: pd.DataFrame, made: str, attempts: str
) -> tuple[pd.Series, pd.Series]:
    """Measure makes above the attempt-weighted player-pool baseline.

    Example: 60% on 100 attempts has more positive impact than 60% on
    10 attempts when the pool baseline is below 60%.
    """
    valid = (
        frame[made].notna()
        & frame[attempts].notna()
        & (frame[attempts] > 0)
    )
    percentage = pd.Series(np.nan, index=frame.index, dtype="float64")
    impact = pd.Series(np.nan, index=frame.index, dtype="float64")
    if not valid.any():
        return percentage, impact

    percentage.loc[valid] = (
        100.0 * frame.loc[valid, made] / frame.loc[valid, attempts]
    )
    baseline = frame.loc[valid, made].sum() / frame.loc[valid, attempts].sum()
    impact.loc[valid] = (
        frame.loc[valid, made] - baseline * frame.loc[valid, attempts]
    )
    return percentage, impact


def calculate_rankings(projections: pd.DataFrame) -> pd.DataFrame:
    """Rank players using nine season-total categories, excluding TW.

    Z-scores use the population standard deviation (ddof=0). FG% and FT%
    use volume-weighted impacts rather than raw percentage Z-scores.
    A complete score requires all nine category Z-scores to be available.
    """
    missing = REQUIRED_COLUMNS - set(projections.columns)
    if missing:
        raise ValueError(f"Missing projection columns: {', '.join(sorted(missing))}")

    frame = projections.copy()
    if frame["player_id"].duplicated().any():
        raise ValueError("Each player_id must occur only once per ranking source.")

    number_columns = [*STAT_COLUMNS, "fgm", "fga", "ftm", "fta"]
    for column in number_columns:
        frame[column] = pd.to_numeric(frame[column], errors="raise")
        if (frame[column].dropna() < 0).any():
            raise ValueError(f"Negative values are not valid for {column}.")

    for made, attempts in (("fgm", "fga"), ("ftm", "fta")):
        paired = frame[made].notna() == frame[attempts].notna()
        if not paired.all() or (frame[made] > frame[attempts]).any():
            raise ValueError(f"Invalid {made}/{attempts} projection values.")

    for stat, score_column in STAT_COLUMNS.items():
        frame[score_column] = _z_score(
            frame[stat], lower_is_better=(stat == "turnovers")
        )

    frame["fg_pct"], fg_impact = _percentage_impact(frame, "fgm", "fga")
    frame["ft_pct"], ft_impact = _percentage_impact(frame, "ftm", "fta")
    frame["z_fg_pct"] = _z_score(fg_impact)
    frame["z_ft_pct"] = _z_score(ft_impact)

    score_cols = list(SCORE_COLUMNS.values())
    frame["categories_available"] = frame[score_cols].notna().sum(axis=1)
    frame["missing_categories"] = frame.apply(
        lambda row: ", ".join(
            category for category, score in SCORE_COLUMNS.items()
            if pd.isna(row[score])
        ),
        axis=1,
    )

    # Never present a partial nine-category total as a comparable full rank.
    frame["z_total"] = frame[score_cols].sum(
        axis=1, min_count=len(score_cols)
    )
    frame["rank"] = frame["z_total"].rank(
        method="min", ascending=False
    ).astype("Int64")

    return frame.sort_values(
        ["z_total", "full_name"],
        ascending=[False, True],
        na_position="last",
        kind="stable",
    ).reset_index(drop=True)


def load_rankings(
    source: str,
    db_path: str | Path = DEFAULT_DB_PATH,
    season: str = SEASON,
) -> pd.DataFrame:
    """Read one projection source from SQLite and calculate its rankings."""
    if not source.strip():
        raise ValueError("Projection source cannot be empty.")

    query = """
        SELECT p.id AS player_id, p.full_name, p.nba_team,
               pr.is_demo, pr.games, pr.pts, pr.reb, pr.ast,
               pr.stl, pr.blk, pr.three_pm, pr.fgm, pr.fga,
               pr.ftm, pr.fta, pr.turnovers, pr.team_wins
        FROM projections AS pr
        JOIN players AS p ON p.id = pr.player_id
        WHERE pr.season = ? AND pr.source = ?
        ORDER BY p.id
    """
    with get_connection(db_path) as connection:
        cursor = connection.execute(query, (season, source.strip()))
        column_names = [column[0] for column in cursor.description]
        rows = [dict(row) for row in cursor.fetchall()]

    frame = pd.DataFrame.from_records(rows, columns=column_names)
    return calculate_rankings(frame)
