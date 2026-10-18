"""Read draft sessions and merge persistent availability with source rankings."""

from pathlib import Path

import pandas as pd

from nba_fantasy_lab.database import DEFAULT_DB_PATH, get_connection
from nba_fantasy_lab.draft_engine import list_available_players
from nba_fantasy_lab.ranking import load_rankings


LEAGUE_NAME = "Koszobidon Fantasy"
SEASON = "2026/27"


def list_sessions(db_path: str | Path = DEFAULT_DB_PATH) -> list[dict]:
    """List saved draft sessions for this league, newest first."""
    with get_connection(db_path) as connection:
        rows = connection.execute(
            """SELECT ds.id, ds.name, ds.status, ds.created_at
               FROM draft_sessions AS ds
               JOIN league_config AS lc ON lc.id = ds.league_id
               WHERE lc.name = ? AND lc.season = ?
               ORDER BY ds.id DESC""",
            (LEAGUE_NAME, SEASON),
        ).fetchall()
        return [dict(row) for row in rows]


def available_rankings(
    session_id: int,
    source: str,
    db_path: str | Path = DEFAULT_DB_PATH,
) -> pd.DataFrame:
    """Preserve full-pool ranks while excluding already drafted players.

    The underlying season-total Z-score population is not recalculated after
    each pick. This keeps draft-board ranks comparable throughout the session.
    """
    ranking = load_rankings(source, db_path=db_path)
    # The draft engine validates the session and provides authoritative IDs.
    available = list_available_players(session_id, source, db_path=db_path)
    ids = {int(row["id"]) for row in available}
    if ranking.empty:
        return ranking.assign(positions=pd.Series(dtype="str"))

    result = ranking.loc[ranking["player_id"].isin(ids)].copy()
    with get_connection(db_path) as connection:
        rows = connection.execute(
            """SELECT pp.player_id, pos.code
               FROM player_positions AS pp
               JOIN positions AS pos ON pos.id = pp.position_id
               ORDER BY pp.player_id, pos.id"""
        ).fetchall()

    positions: dict[int, list[str]] = {}
    for row in rows:
        positions.setdefault(row["player_id"], []).append(row["code"])
    result["positions"] = result["player_id"].map(
        lambda value: "/".join(positions.get(int(value), []))
    )
    return result.reset_index(drop=True)
