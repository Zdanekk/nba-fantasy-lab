
"""Walidacja plików CSV i trwały import prognoz do SQLite."""

import csv
import io
import math
from pathlib import Path

from nba_fantasy_lab.database import POSITIONS, get_connection

SEASON = "2026/27"
REQUIRED_COLUMNS = {"full_name", "nba_team", "positions"}
STAT_COLUMNS = (
    "pts", "reb", "ast", "stl", "blk", "three_pm",
    "fgm", "fga", "ftm", "fta", "turnovers", "team_wins",
)


def _number(raw: str | None, column: str, row_number: int) -> float | None:
    if raw is None or not raw.strip():
        return None
    try:
        number = float(raw.strip())
    except ValueError as exc:
        raise ValueError(f"Wiersz {row_number}: {column} nie jest liczbą.") from exc
    if not math.isfinite(number) or number < 0:
        raise ValueError(
            f"Wiersz {row_number}: {column} musi być liczbą nieujemną."
        )
    return number


def parse_csv(contents: bytes) -> list[dict]:
    """Zweryfikuj cały CSV przed jakimkolwiek zapisem do bazy."""
    try:
        text = contents.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("Plik CSV musi być zapisany w UTF-8.") from exc

    reader = csv.DictReader(io.StringIO(text, newline=""))
    if reader.fieldnames is None:
        raise ValueError("Plik CSV nie ma nagłówka.")

    reader.fieldnames = [name.strip() for name in reader.fieldnames]
    if len(reader.fieldnames) != len(set(reader.fieldnames)):
        raise ValueError("Nagłówek CSV zawiera zduplikowane kolumny.")

    missing = REQUIRED_COLUMNS - set(reader.fieldnames)
    if missing:
        raise ValueError(
            f"Brak wymaganych kolumn CSV: {', '.join(sorted(missing))}."
        )

    records = []
    seen = set()

    for row_number, raw_row in enumerate(reader, start=2):
        if None in raw_row:
            raise ValueError(
                f"Wiersz {row_number}: za dużo pól względem nagłówka."
            )

        name = (raw_row["full_name"] or "").strip()
        team = (raw_row["nba_team"] or "").strip().upper()
        positions = [
            pos.strip().upper()
            for pos in (raw_row["positions"] or "").split("|")
        ]

        if not name or not team:
            raise ValueError(
                f"Wiersz {row_number}: zawodnik i zespół są wymagane."
            )
        if not positions or any(pos not in POSITIONS for pos in positions):
            raise ValueError(
                f"Wiersz {row_number}: niepoprawne pozycje (PG|SG|SF|PF|C)."
            )

        identity = (name.casefold(), team)
        if identity in seen:
            raise ValueError(
                f"Wiersz {row_number}: zawodnik powtarza się w pliku."
            )
        seen.add(identity)

        games = _number(raw_row.get("games"), "games", row_number)
        if games is not None and not games.is_integer():
            raise ValueError(
                f"Wiersz {row_number}: games musi być liczbą całkowitą."
            )

        stats = {
            col: _number(raw_row.get(col), col, row_number)
            for col in STAT_COLUMNS
        }

        for made, attempts in (("fgm", "fga"), ("ftm", "fta")):
            if (stats[made] is None) != (stats[attempts] is None):
                raise ValueError(
                    f"Wiersz {row_number}: {made} i {attempts} muszą wystąpić razem."
                )
            if stats[made] is not None and stats[made] > stats[attempts]:
                raise ValueError(
                    f"Wiersz {row_number}: {made} nie może przekraczać {attempts}."
                )

        records.append({
            "full_name": name,
            "nba_team": team,
            "positions": sorted(set(positions)),
            "games": None if games is None else int(games),
            **stats,
        })

    if not records:
        raise ValueError("Plik CSV nie zawiera żadnych zawodników.")

    return records


def import_projections(
    contents: bytes,
    *,
    db_path: str | Path,
    source: str,
    is_demo: bool,
    season: str = SEASON,
) -> int:
    """Zaimportuj lub zaktualizuj prognozy bez duplikatów."""
    if not source.strip():
        raise ValueError("Nazwa źródła nie może być pusta.")

    records = parse_csv(contents)
    columns = ("games", *STAT_COLUMNS)
    insert_columns = ("player_id", "season", "source", "is_demo", *columns)
    placeholders = ", ".join("?" for _ in insert_columns)
    assignments = ", ".join(
        f"{col} = excluded.{col}"
        for col in ("is_demo", *columns)
    )

    statement = (
        f"INSERT INTO projections ({', '.join(insert_columns)}) "
        f"VALUES ({placeholders}) "
        f"ON CONFLICT(player_id, season, source) DO UPDATE SET "
        f"{assignments}, updated_at = CURRENT_TIMESTAMP"
    )

    with get_connection(db_path) as connection:
        positions = {
            row["code"]: row["id"]
            for row in connection.execute("SELECT id, code FROM positions")
        }

        for rec in records:
            candidates = connection.execute(
                "SELECT id FROM players "
                "WHERE full_name = ? COLLATE NOCASE "
                "AND nba_team = ? COLLATE NOCASE",
                (rec["full_name"], rec["nba_team"]),
            ).fetchall()

            if len(candidates) > 1:
                raise ValueError(
                    f"Niejednoznaczny zawodnik: {rec['full_name']}."
                )

            if candidates:
                player_id = candidates[0]["id"]
            else:
                player_id = connection.execute(
                    "INSERT INTO players(full_name, nba_team) VALUES (?, ?)",
                    (rec["full_name"], rec["nba_team"]),
                ).lastrowid

            for position in rec["positions"]:
                connection.execute(
                    "INSERT OR IGNORE INTO player_positions "
                    "(player_id, position_id) VALUES (?, ?)",
                    (player_id, positions[position]),
                )

            values = (
                player_id, season, source.strip(), int(is_demo),
                *(rec[col] for col in columns),
            )
            connection.execute(statement, values)

    return len(records)
