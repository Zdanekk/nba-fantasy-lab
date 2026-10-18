"""Integration tests for ranked draft availability and persistent sessions."""

import pytest

from nba_fantasy_lab.database import get_connection, initialize_database
from nba_fantasy_lab.draft_engine import (
    create_draft_session,
    list_pick_events,
    make_pick,
    undo_last_pick,
)
from nba_fantasy_lab.draft_view import available_rankings, list_sessions


@pytest.fixture
def prepared_db(tmp_path):
    """Create a small complete source with distinct statistical profiles."""
    path = tmp_path / "draft_view.sqlite3"
    initialize_database(path)
    with get_connection(path) as connection:
        connection.executescript("""
            CREATE TABLE IF NOT EXISTS positions (
                id INTEGER PRIMARY KEY, code TEXT UNIQUE NOT NULL
            );
            CREATE TABLE IF NOT EXISTS player_positions (
                player_id INTEGER NOT NULL REFERENCES players(id),
                position_id INTEGER NOT NULL REFERENCES positions(id),
                PRIMARY KEY (player_id, position_id)
            );
        """)
        for code in ("PG", "SG", "SF", "PF", "C"):
            connection.execute(
                "INSERT OR IGNORE INTO positions(code) VALUES (?)", (code,)
            )
    projections = [
        ("Player One", "PG", 100, 20, 30, 5, 2, 20, 30, 60, 15, 20, 10),
        ("Player Two", "C", 200, 70, 10, 10, 8, 1, 80, 140, 20, 30, 20),
        ("Player Three", "SF", 150, 40, 20, 8, 4, 10, 55, 110, 40, 50, 15),
        ("Player Four", "SG", 180, 35, 40, 6, 3, 28, 70, 140, 60, 75, 23),
    ]
    with get_connection(path) as connection:
        position_ids = {
            row["code"]: row["id"]
            for row in connection.execute("SELECT id, code FROM positions")
        }
        for name, position, *stats in projections:
            player_id = connection.execute(
                "INSERT INTO players(full_name, nba_team) VALUES (?, 'DEM')",
                (name,),
            ).lastrowid
            connection.execute(
                "INSERT INTO player_positions(player_id, position_id) VALUES (?, ?)",
                (player_id, position_ids[position]),
            )
            connection.execute(
                """INSERT INTO projections (
                     player_id, season, source, is_demo, pts, reb, ast, stl,
                     blk, three_pm, fgm, fga, ftm, fta, turnovers
                   ) VALUES (?, '2026/27', 'test_source', 1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (player_id, *stats),
            )
    return path


def new_session(path, name="Draft A"):
    return create_draft_session(
        name, [f"Team {index}" for index in range(1, 13)], db_path=path,
    )


def test_board_excludes_drafted_player_and_preserves_original_rank(prepared_db):
    session_id = new_session(prepared_db)
    before = available_rankings(session_id, "test_source", prepared_db)
    assert len(before) == 4
    assert set(before["positions"]) == {"PG", "SG", "SF", "C"}
    assert before["team_wins"].isna().all()
    assert before["categories_available"].eq(9).all()

    drafted = int(before.iloc[0]["player_id"])
    comparison = before.loc[before["player_id"] != drafted, ["player_id", "z_total"]]
    make_pick(session_id, drafted, prepared_db)
    after = available_rankings(session_id, "test_source", prepared_db)
    assert len(after) == 3
    assert drafted not in after["player_id"].tolist()
    for row in comparison.itertuples(index=False):
        value = after.loc[after["player_id"] == row.player_id, "z_total"].iloc[0]
        assert value == pytest.approx(row.z_total)


def test_undo_restores_player_and_persists_events(prepared_db):
    session_id = new_session(prepared_db)
    make_pick(session_id, 1, prepared_db)
    assert len(available_rankings(session_id, "test_source", prepared_db)) == 3
    undo_last_pick(session_id, prepared_db)
    assert len(available_rankings(session_id, "test_source", prepared_db)) == 4
    assert [e["event_type"] for e in list_pick_events(session_id, prepared_db)] == [
        "pick", "undo"
    ]


def test_sessions_list_tracks_creation_order_and_persistent_status(prepared_db):
    first_id = new_session(prepared_db, "Draft A")
    second_id = new_session(prepared_db, "Draft B")
    make_pick(first_id, 1, prepared_db)
    rows = list_sessions(prepared_db)
    assert [row["id"] for row in rows] == [second_id, first_id]
    assert [row["status"] for row in rows] == ["setup", "in_progress"]


def test_draft_sessions_have_independent_availability(prepared_db):
    first_id = new_session(prepared_db, "Draft A")
    second_id = new_session(prepared_db, "Draft B")
    make_pick(first_id, 1, prepared_db)
    assert 1 not in available_rankings(first_id, "test_source", prepared_db)["player_id"].tolist()
    assert 1 in available_rankings(second_id, "test_source", prepared_db)["player_id"].tolist()
