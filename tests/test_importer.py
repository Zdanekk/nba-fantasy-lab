
"""Tests for CSV validation and persistent projection imports."""

from pathlib import Path

import pytest

from nba_fantasy_lab.database import get_connection, initialize_database
from nba_fantasy_lab.importer import import_projections, parse_csv

DEMO_FILE = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "demo_projections.csv"
)


def test_import_demo_and_persistence(tmp_path):
    db_path = tmp_path / "test.sqlite3"
    initialize_database(db_path)

    count = import_projections(
        DEMO_FILE.read_bytes(),
        db_path=db_path,
        source="demo_phase01",
        is_demo=True,
    )
    assert count == 12

    with get_connection(db_path) as connection:
        row = connection.execute(
            "SELECT COUNT(*) AS total, "
            "SUM(is_demo) AS demo, "
            "COUNT(team_wins) AS known_tw FROM projections"
        ).fetchone()

        assert (
            row["total"], row["demo"], row["known_tw"]
        ) == (12, 12, 0)

        positions = connection.execute(
            "SELECT COUNT(*) FROM player_positions"
        ).fetchone()[0]
        assert positions > 12


def test_reimport_does_not_duplicate(tmp_path):
    db_path = tmp_path / "test.sqlite3"
    initialize_database(db_path)

    for _ in range(2):
        import_projections(
            DEMO_FILE.read_bytes(),
            db_path=db_path,
            source="demo_phase01",
            is_demo=True,
        )

    with get_connection(db_path) as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM players"
        ).fetchone()[0] == 12

        assert connection.execute(
            "SELECT COUNT(*) FROM projections"
        ).fetchone()[0] == 12


def test_invalid_csv_never_writes_partial_data(tmp_path):
    db_path = tmp_path / "test.sqlite3"
    initialize_database(db_path)

    data = (
        "full_name,nba_team,positions,fgm,fga\n"
        "Good One,DEM,PG,2,4\n"
        "Bad One,DEM,SF,9,3\n"
    ).encode("utf-8")

    with pytest.raises(ValueError, match="fgm"):
        import_projections(
            data,
            db_path=db_path,
            source="user_csv",
            is_demo=False,
        )

    with get_connection(db_path) as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM players"
        ).fetchone()[0] == 0


def test_missing_values_not_replaced_with_zero():
    rows = parse_csv(
        b"full_name,nba_team,positions,pts\nTester,DEM,C,\n"
    )

    assert rows[0]["pts"] is None
    assert rows[0]["team_wins"] is None
