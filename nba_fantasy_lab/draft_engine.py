"""Pure draft-order logic and persistent SQLite draft operations."""

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from nba_fantasy_lab.database import DEFAULT_DB_PATH, get_connection


class DraftError(ValueError):
    """Raised when a draft operation violates a business rule."""


@dataclass(frozen=True)
class DraftTurn:
    overall_pick: int
    round_number: int
    pick_in_round: int
    draft_slot: int


def snake_turn(overall_pick: int, team_count: int = 12) -> DraftTurn:
    """Return the team slot for a one-based overall pick."""
    if team_count < 2 or overall_pick < 1:
        raise DraftError("Team count must be >= 2 and pick number must be >= 1.")
    round_index, zero_based_pick = divmod(overall_pick - 1, team_count)
    draft_slot = (
        zero_based_pick + 1
        if round_index % 2 == 0
        else team_count - zero_based_pick
    )
    return DraftTurn(
        overall_pick=overall_pick,
        round_number=round_index + 1,
        pick_in_round=zero_based_pick + 1,
        draft_slot=draft_slot,
    )


def snake_schedule(team_count: int = 12, rounds: int = 13) -> list[DraftTurn]:
    """Build the entire snake draft schedule without accessing the database."""
    if team_count < 2 or rounds < 1:
        raise DraftError("Team count must be >= 2 and rounds must be >= 1.")
    return [snake_turn(i, team_count) for i in range(1, team_count * rounds + 1)]


def _validate_team_names(team_names: Sequence[str], team_count: int) -> list[str]:
    if isinstance(team_names, str) or len(team_names) != team_count:
        raise DraftError(f"Exactly {team_count} teams are required.")
    names = [name.strip() if isinstance(name, str) else "" for name in team_names]
    if any(not name for name in names):
        raise DraftError("Team names cannot be empty.")
    if len({name.casefold() for name in names}) != team_count:
        raise DraftError("Team names must be unique (case-insensitive).")
    return names


def _session(connection, session_id: int):
    session = connection.execute(
        """SELECT ds.id, ds.name, ds.status, lc.team_count, lc.draft_rounds,
                  lc.season
           FROM draft_sessions ds
           JOIN league_config lc ON lc.id = ds.league_id
           WHERE ds.id = ?""",
        (session_id,),
    ).fetchone()
    if session is None:
        raise DraftError(f"Draft session {session_id} does not exist.")
    return session


def _teams(connection, session_id: int) -> dict[int, dict]:
    rows = connection.execute(
        """SELECT id, draft_slot, team_name FROM draft_teams
           WHERE session_id = ? ORDER BY draft_slot""",
        (session_id,),
    ).fetchall()
    return {row["draft_slot"]: dict(row) for row in rows}


def create_draft_session(
    name: str,
    team_names: Sequence[str],
    db_path: str | Path = DEFAULT_DB_PATH,
) -> int:
    """Create a session with a complete, ordered set of league teams."""
    if not isinstance(name, str) or not name.strip():
        raise DraftError("Draft session name cannot be empty.")
    with get_connection(db_path) as connection:
        connection.execute("BEGIN IMMEDIATE")
        league = connection.execute(
            """SELECT id, team_count FROM league_config
               WHERE name = ? AND season = ?""",
            ("Koszobidon Fantasy", "2026/27"),
        ).fetchone()
        if league is None:
            raise DraftError("League configuration not found. Initialize the database first.")
        names = _validate_team_names(team_names, league["team_count"])
        session_id = connection.execute(
            "INSERT INTO draft_sessions(league_id, name) VALUES (?, ?)",
            (league["id"], name.strip()),
        ).lastrowid
        connection.executemany(
            """INSERT INTO draft_teams(session_id, draft_slot, team_name)
               VALUES (?, ?, ?)""",
            [(session_id, i, team_name) for i, team_name in enumerate(names, 1)],
        )
        return session_id


def set_draft_order(
    session_id: int,
    team_names: Sequence[str],
    db_path: str | Path = DEFAULT_DB_PATH,
) -> None:
    """Replace draft-slot assignments before any pick or undo event exists."""
    with get_connection(db_path) as connection:
        connection.execute("BEGIN IMMEDIATE")
        session = _session(connection, session_id)
        names = _validate_team_names(team_names, session["team_count"])
        if session["status"] != "setup":
            raise DraftError("Draft order is locked after the draft starts.")
        if connection.execute(
            "SELECT 1 FROM draft_pick_events WHERE session_id = ? LIMIT 1",
            (session_id,),
        ).fetchone():
            raise DraftError("Draft order is locked after the first recorded pick.")
        connection.execute("DELETE FROM draft_teams WHERE session_id = ?", (session_id,))
        connection.executemany(
            """INSERT INTO draft_teams(session_id, draft_slot, team_name)
               VALUES (?, ?, ?)""",
            [(session_id, i, team_name) for i, team_name in enumerate(names, 1)],
        )


def get_draft_state(
    session_id: int, db_path: str | Path = DEFAULT_DB_PATH,
) -> dict:
    """Return progress and the next team on the clock."""
    with get_connection(db_path) as connection:
        session = _session(connection, session_id)
        teams = _teams(connection, session_id)
        if len(teams) != session["team_count"] or set(teams) != set(
            range(1, session["team_count"] + 1)
        ):
            raise DraftError("All draft slots must be assigned before drafting.")
        completed = connection.execute(
            "SELECT COUNT(*) FROM draft_picks WHERE session_id = ?", (session_id,)
        ).fetchone()[0]
        total = session["team_count"] * session["draft_rounds"]
        next_turn = snake_turn(completed + 1, session["team_count"]) if completed < total else None
        return {
            "session_id": session_id,
            "name": session["name"],
            "status": session["status"],
            "completed_picks": completed,
            "total_picks": total,
            "next_turn": next_turn,
            "next_team": teams[next_turn.draft_slot]["team_name"] if next_turn else None,
            "teams": teams,
        }


def make_pick(
    session_id: int,
    player_id: int,
    db_path: str | Path = DEFAULT_DB_PATH,
) -> DraftTurn:
    """Draft the next player atomically and append a permanent audit event."""
    with get_connection(db_path) as connection:
        connection.execute("BEGIN IMMEDIATE")
        session = _session(connection, session_id)
        if session["status"] == "finished":
            raise DraftError("Draft is finished.")
        teams = _teams(connection, session_id)
        if set(teams) != set(range(1, session["team_count"] + 1)):
            raise DraftError("All draft slots must be assigned before drafting.")
        count = connection.execute(
            "SELECT COUNT(*) FROM draft_picks WHERE session_id = ?", (session_id,)
        ).fetchone()[0]
        total = session["team_count"] * session["draft_rounds"]
        if count >= total:
            raise DraftError("All draft picks have been used.")
        if not connection.execute(
            "SELECT 1 FROM players WHERE id = ?", (player_id,)
        ).fetchone():
            raise DraftError("Player does not exist.")
        if connection.execute(
            "SELECT 1 FROM draft_picks WHERE session_id = ? AND player_id = ?",
            (session_id, player_id),
        ).fetchone():
            raise DraftError("Player has already been drafted in this session.")
        turn = snake_turn(count + 1, session["team_count"])
        connection.execute(
            """INSERT INTO draft_picks(
                   session_id, draft_team_id, player_id, overall_pick,
                   round_number, pick_in_round
               ) VALUES (?, ?, ?, ?, ?, ?)""",
            (
                session_id, teams[turn.draft_slot]["id"], player_id,
                turn.overall_pick, turn.round_number, turn.pick_in_round,
            ),
        )
        connection.execute(
            """INSERT INTO draft_pick_events(session_id, player_id, overall_pick, event_type)
               VALUES (?, ?, ?, 'pick')""",
            (session_id, player_id, turn.overall_pick),
        )
        connection.execute(
            "UPDATE draft_sessions SET status = ? WHERE id = ?",
            ("finished" if count + 1 == total else "in_progress", session_id),
        )
        return turn


def undo_last_pick(
    session_id: int, db_path: str | Path = DEFAULT_DB_PATH,
) -> int:
    """Undo only the most recent pick, keeping the immutable event history."""
    with get_connection(db_path) as connection:
        connection.execute("BEGIN IMMEDIATE")
        _session(connection, session_id)
        pick = connection.execute(
            """SELECT player_id, overall_pick FROM draft_picks
               WHERE session_id = ? ORDER BY overall_pick DESC LIMIT 1""",
            (session_id,),
        ).fetchone()
        if pick is None:
            raise DraftError("No draft pick is available to undo.")
        connection.execute(
            "DELETE FROM draft_picks WHERE session_id = ? AND overall_pick = ?",
            (session_id, pick["overall_pick"]),
        )
        connection.execute(
            """INSERT INTO draft_pick_events(session_id, player_id, overall_pick, event_type)
               VALUES (?, ?, ?, 'undo')""",
            (session_id, pick["player_id"], pick["overall_pick"]),
        )
        connection.execute(
            "UPDATE draft_sessions SET status = 'in_progress' WHERE id = ?",
            (session_id,),
        )
        return pick["player_id"]


def list_draft_picks(
    session_id: int, db_path: str | Path = DEFAULT_DB_PATH,
) -> list[dict]:
    """Return current selections in overall-pick order."""
    with get_connection(db_path) as connection:
        _session(connection, session_id)
        rows = connection.execute(
            """SELECT dp.overall_pick, dp.round_number, dp.pick_in_round,
                      dt.draft_slot, dt.team_name, p.id AS player_id, p.full_name
               FROM draft_picks dp
               JOIN draft_teams dt ON dt.id = dp.draft_team_id
               JOIN players p ON p.id = dp.player_id
               WHERE dp.session_id = ? ORDER BY dp.overall_pick""",
            (session_id,),
        ).fetchall()
        return [dict(row) for row in rows]


def list_available_players(
    session_id: int,
    source: str,
    db_path: str | Path = DEFAULT_DB_PATH,
) -> list[dict]:
    """List players from a projection source who are not currently drafted."""
    with get_connection(db_path) as connection:
        session = _session(connection, session_id)
        rows = connection.execute(
            """SELECT p.id, p.full_name, p.nba_team
               FROM players p
               JOIN projections pr ON pr.player_id = p.id
               WHERE pr.season = ? AND pr.source = ?
                 AND NOT EXISTS (
                     SELECT 1 FROM draft_picks dp
                     WHERE dp.session_id = ? AND dp.player_id = p.id
                 )
               ORDER BY p.full_name""",
            (session["season"], source, session_id),
        ).fetchall()
        return [dict(row) for row in rows]


def list_pick_events(
    session_id: int, db_path: str | Path = DEFAULT_DB_PATH,
) -> list[dict]:
    """Return the persistent pick/undo audit trail in event order."""
    with get_connection(db_path) as connection:
        _session(connection, session_id)
        rows = connection.execute(
            """SELECT e.id, e.overall_pick, e.event_type, e.created_at,
                      p.id AS player_id, p.full_name
               FROM draft_pick_events e
               JOIN players p ON p.id = e.player_id
               WHERE e.session_id = ? ORDER BY e.id""",
            (session_id,),
        ).fetchall()
        return [dict(row) for row in rows]
