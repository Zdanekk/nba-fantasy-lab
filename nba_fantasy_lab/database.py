
"""Schemat SQLite, połączenia i inicjalizacja lokalnej bazy danych."""

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "nba_fantasy_lab.sqlite3"

POSITIONS = ("PG", "SG", "SF", "PF", "C")

ROSTER_SLOTS = {
    "PG": 1, "SG": 1, "SF": 1, "PF": 1, "C": 1,
    "G": 1, "F": 1, "UTIL": 3, "BE": 3, "IR": 1,
}

SCORING_CATEGORIES = {
    "PTS": "higher", "REB": "higher", "AST": "higher",
    "STL": "higher", "BLK": "higher", "3PM": "higher",
    "FG%": "higher", "FT%": "higher", "TO": "lower",
    "TW": "unverified",
}

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS league_config (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    season TEXT NOT NULL,
    platform TEXT NOT NULL,
    scoring_format TEXT NOT NULL,
    team_count INTEGER NOT NULL CHECK(team_count > 1),
    draft_rounds INTEGER NOT NULL CHECK(draft_rounds > 0),
    pick_seconds INTEGER NOT NULL CHECK(pick_seconds > 0),
    weekly_add_limit INTEGER NOT NULL CHECK(weekly_add_limit >= 0),
    roster_slots_json TEXT NOT NULL,
    categories_json TEXT NOT NULL,
    tw_rule_verified INTEGER NOT NULL DEFAULT 0
        CHECK(tw_rule_verified IN (0, 1)),
    tw_rule_notes TEXT,
    UNIQUE(name, season)
);

CREATE TABLE IF NOT EXISTS players (
    id INTEGER PRIMARY KEY,
    full_name TEXT NOT NULL,
    nba_team TEXT,
    espn_player_id TEXT UNIQUE,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS positions (
    id INTEGER PRIMARY KEY,
    code TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS player_positions (
    player_id INTEGER NOT NULL REFERENCES players(id) ON DELETE CASCADE,
    position_id INTEGER NOT NULL REFERENCES positions(id),
    PRIMARY KEY (player_id, position_id)
);

-- Surowe liczniki do Z-score; FG% i FT% liczymy z celnych/prób.
-- NULL = brak prognozy. Nie wstawiamy fikcyjnych zer.
CREATE TABLE IF NOT EXISTS projections (
    id INTEGER PRIMARY KEY,
    player_id INTEGER NOT NULL REFERENCES players(id) ON DELETE CASCADE,
    season TEXT NOT NULL,
    source TEXT NOT NULL,
    is_demo INTEGER NOT NULL DEFAULT 0 CHECK(is_demo IN (0, 1)),
    games INTEGER CHECK(games >= 0),
    pts REAL, reb REAL, ast REAL, stl REAL, blk REAL,
    three_pm REAL, fgm REAL, fga REAL, ftm REAL, fta REAL,
    turnovers REAL, team_wins REAL,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(player_id, season, source),
    CHECK(fgm IS NULL OR fga IS NULL OR (fgm >= 0 AND fgm <= fga)),
    CHECK(ftm IS NULL OR fta IS NULL OR (ftm >= 0 AND ftm <= fta))
);

CREATE TABLE IF NOT EXISTS draft_sessions (
    id INTEGER PRIMARY KEY,
    league_id INTEGER NOT NULL REFERENCES league_config(id),
    name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'setup'
        CHECK(status IN ('setup', 'in_progress', 'finished')),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS draft_teams (
    id INTEGER PRIMARY KEY,
    session_id INTEGER NOT NULL REFERENCES draft_sessions(id) ON DELETE CASCADE,
    draft_slot INTEGER NOT NULL CHECK(draft_slot > 0),
    team_name TEXT NOT NULL,
    UNIQUE(session_id, draft_slot),
    UNIQUE(session_id, team_name),
    UNIQUE(id, session_id)
);

CREATE TABLE IF NOT EXISTS draft_picks (
    id INTEGER PRIMARY KEY,
    session_id INTEGER NOT NULL REFERENCES draft_sessions(id) ON DELETE CASCADE,
    draft_team_id INTEGER NOT NULL,
    player_id INTEGER NOT NULL REFERENCES players(id),
    overall_pick INTEGER NOT NULL CHECK(overall_pick > 0),
    round_number INTEGER NOT NULL CHECK(round_number > 0),
    pick_in_round INTEGER NOT NULL CHECK(pick_in_round > 0),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(draft_team_id, session_id)
        REFERENCES draft_teams(id, session_id),
    UNIQUE(session_id, overall_pick),
    UNIQUE(session_id, player_id),
    UNIQUE(session_id, round_number, pick_in_round)
);

-- Dziennik pozwoli zachować ślad także po cofnięciu wyboru.
CREATE TABLE IF NOT EXISTS draft_pick_events (
    id INTEGER PRIMARY KEY,
    session_id INTEGER NOT NULL REFERENCES draft_sessions(id) ON DELETE CASCADE,
    player_id INTEGER NOT NULL REFERENCES players(id),
    overall_pick INTEGER NOT NULL CHECK(overall_pick > 0),
    event_type TEXT NOT NULL CHECK(event_type IN ('pick', 'undo')),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_player_names ON players(full_name);
CREATE INDEX IF NOT EXISTS idx_projections_season ON projections(season);
CREATE INDEX IF NOT EXISTS idx_draft_picks_session ON draft_picks(session_id);
CREATE INDEX IF NOT EXISTS idx_pick_events_session ON draft_pick_events(session_id);
"""


@contextmanager
def get_connection(
    db_path: str | Path = DEFAULT_DB_PATH,
) -> Iterator[sqlite3.Connection]:
    """Otwórz połączenie; commit przy sukcesie, rollback przy błędzie."""
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def initialize_database(
    db_path: str | Path = DEFAULT_DB_PATH,
) -> None:
    """Utwórz brakujące tabele i dane startowe bez kasowania wyborów."""
    with get_connection(db_path) as connection:
        connection.executescript(SCHEMA_SQL)
        connection.executemany(
            "INSERT OR IGNORE INTO positions(code) VALUES (?)",
            [(code,) for code in POSITIONS],
        )
        connection.execute(
            """
            INSERT OR IGNORE INTO league_config (
                name, season, platform, scoring_format, team_count,
                draft_rounds, pick_seconds, weekly_add_limit,
                roster_slots_json, categories_json,
                tw_rule_verified, tw_rule_notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "Koszobidon Fantasy", "2026/27", "ESPN Fantasy Basketball",
                "Head to Head Each Category", 12, 13, 90, 7,
                json.dumps(ROSTER_SLOTS), json.dumps(SCORING_CATEGORIES),
                0, "Reguła ESPN Team Wins wymaga weryfikacji.",
            ),
        )


if __name__ == "__main__":
    initialize_database()
    print(f"SQLite OK: {DEFAULT_DB_PATH}")
