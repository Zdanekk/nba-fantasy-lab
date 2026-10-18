"""Unit and integration tests for the persistent snake draft engine."""

import pytest

from nba_fantasy_lab.database import get_connection, initialize_database
from nba_fantasy_lab.draft_engine import (
    DraftError,
    create_draft_session,
    get_draft_state,
    list_available_players,
    list_draft_picks,
    list_pick_events,
    make_pick,
    set_draft_order,
    snake_schedule,
    snake_turn,
    undo_last_pick,
)


@pytest.fixture
def draft_db(tmp_path):
    path = tmp_path / "draft.sqlite3"
    initialize_database(path)
    with get_connection(path) as connection:
        for i in range(1, 158):
            connection.execute(
                "INSERT INTO players(full_name, nba_team) VALUES (?, ?)",
                (f"Test Player {i:03d}", "DEM"),
            )
            connection.execute(
                """INSERT INTO projections(player_id, season, source, is_demo)
                   VALUES (?, '2026/27', 'demo_phase01', 1)""",
                (i,),
            )
    return path


def _new_session(path):
    return create_draft_session(
        "Test draft", [f"Team {i}" for i in range(1, 13)], db_path=path
    )


def test_snake_schedule_has_156_turns():
    schedule = snake_schedule()
    assert len(schedule) == 156
    assert [turn.draft_slot for turn in schedule[:12]] == list(range(1, 13))
    assert [turn.draft_slot for turn in schedule[12:24]] == list(range(12, 0, -1))
    assert [turn.draft_slot for turn in schedule[24:36]] == list(range(1, 13))
    assert schedule[12] == snake_turn(13)
    assert schedule[-1].round_number == 13
    assert schedule[-1].draft_slot == 12


def test_order_can_change_only_before_first_pick(draft_db):
    session_id = _new_session(draft_db)
    reversed_names = [f"Team {i}" for i in range(12, 0, -1)]
    set_draft_order(session_id, reversed_names, draft_db)
    assert get_draft_state(session_id, draft_db)["next_team"] == "Team 12"
    make_pick(session_id, 1, draft_db)
    undo_last_pick(session_id, draft_db)
    with pytest.raises(DraftError, match="locked"):
        set_draft_order(session_id, reversed_names, draft_db)


def test_pick_duplicate_blocked_and_undo_restores_player(draft_db):
    session_id = _new_session(draft_db)
    available = list_available_players(session_id, "demo_phase01", draft_db)
    assert len(available) == 157
    first = make_pick(session_id, 1, draft_db)
    assert (first.overall_pick, first.round_number, first.draft_slot) == (1, 1, 1)
    assert len(list_available_players(session_id, "demo_phase01", draft_db)) == 156
    with pytest.raises(DraftError, match="already"):
        make_pick(session_id, 1, draft_db)
    assert get_draft_state(session_id, draft_db)["completed_picks"] == 1
    assert undo_last_pick(session_id, draft_db) == 1
    assert len(list_available_players(session_id, "demo_phase01", draft_db)) == 157
    assert list_draft_picks(session_id, draft_db) == []
    assert [e["event_type"] for e in list_pick_events(session_id, draft_db)] == [
        "pick", "undo"
    ]
    with get_connection(draft_db) as connection:
        events = connection.execute(
            "SELECT event_type FROM draft_pick_events WHERE session_id = ? ORDER BY id",
            (session_id,),
        ).fetchall()
    assert [row[0] for row in events] == ["pick", "undo"]


def test_picks_persist_and_second_round_reverses(draft_db):
    session_id = _new_session(draft_db)
    for player_id in range(1, 14):
        make_pick(session_id, player_id, draft_db)
    picks = list_draft_picks(session_id, draft_db)
    assert len(picks) == 13
    assert picks[11]["draft_slot"] == 12
    assert picks[12]["draft_slot"] == 12
    assert get_draft_state(session_id, draft_db)["next_team"] == "Team 11"
    # Use a fresh connection to verify that selections were persisted.
    with get_connection(draft_db) as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM draft_picks WHERE session_id = ?", (session_id,)
        ).fetchone()[0] == 13


def test_fills_all_156_picks_and_undo_reopens(draft_db):
    session_id = _new_session(draft_db)
    for player_id in range(1, 157):
        make_pick(session_id, player_id, draft_db)
    state = get_draft_state(session_id, draft_db)
    assert state["completed_picks"] == 156
    assert state["status"] == "finished"
    assert state["next_turn"] is None
    with pytest.raises(DraftError, match="finished"):
        make_pick(session_id, 157, draft_db)
    undo_last_pick(session_id, draft_db)
    assert get_draft_state(session_id, draft_db)["status"] == "in_progress"
    assert get_draft_state(session_id, draft_db)["next_turn"].overall_pick == 156


def test_invalid_team_order_and_empty_undo(draft_db):
    with pytest.raises(DraftError, match="Exactly 12"):
        create_draft_session("Invalid", ["Only one"], draft_db)
    with pytest.raises(DraftError, match="unique"):
        create_draft_session("Invalid", ["Repeat"] * 12, draft_db)
    session_id = _new_session(draft_db)
    with pytest.raises(DraftError, match="No draft pick"):
        undo_last_pick(session_id, draft_db)
