
"""Basic tests for SQLite schema and data persistence."""

import json
import sqlite3

import pytest

from nba_fantasy_lab.database import get_connection, initialize_database


def test_schema_and_league_configuration(tmp_path):
    db_path = tmp_path / "test.sqlite3"
    initialize_database(db_path)

    with get_connection(db_path) as connection:
        tables = {
            row["name"]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        assert {
            "league_config", "players", "positions", "player_positions",
            "projections", "draft_sessions", "draft_teams",
            "draft_picks", "draft_pick_events",
        }.issubset(tables)

        league = connection.execute("SELECT * FROM league_config").fetchone()
        assert league["name"] == "Koszobidon Fantasy"
        assert league["team_count"] == 12
        assert league["draft_rounds"] == 13
        assert league["pick_seconds"] == 90
        assert league["weekly_add_limit"] == 7
        assert league["tw_rule_verified"] == 0
        assert json.loads(league["categories_json"])["TO"] == "lower"
        assert json.loads(league["categories_json"])["TW"] == "unverified"


def test_initialization_is_repeatable(tmp_path):
    db_path = tmp_path / "test.sqlite3"
    initialize_database(db_path)
    initialize_database(db_path)

    with get_connection(db_path) as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM league_config"
        ).fetchone()[0] == 1
        assert connection.execute(
            "SELECT COUNT(*) FROM positions"
        ).fetchone()[0] == 5


def test_records_survive_reconnecting(tmp_path):
    db_path = tmp_path / "test.sqlite3"
    initialize_database(db_path)

    with get_connection(db_path) as connection:
        connection.execute(
            "INSERT INTO players(full_name, nba_team) VALUES (?, ?)",
            ("Test Player", "TEST"),
        )

    with get_connection(db_path) as connection:
        row = connection.execute("SELECT full_name FROM players").fetchone()
        assert row["full_name"] == "Test Player"


def test_foreign_keys_are_enforced(tmp_path):
    db_path = tmp_path / "test.sqlite3"
    initialize_database(db_path)

    with pytest.raises(sqlite3.IntegrityError):
        with get_connection(db_path) as connection:
            connection.execute(
                "INSERT INTO player_positions(player_id, position_id) VALUES (?, ?)",
                (999, 1),
            )
