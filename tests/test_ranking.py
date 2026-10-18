"""Tests for transparent nine-category Z-score rankings."""

import pandas as pd
import pytest

from nba_fantasy_lab.database import get_connection, initialize_database
from nba_fantasy_lab.ranking import (
    SCORE_COLUMNS,
    calculate_rankings,
    load_rankings,
)


def projections() -> pd.DataFrame:
    """Return independent synthetic player projections for ranking tests."""
    return pd.DataFrame([
        dict(player_id=1, full_name="Low Volume", pts=100, reb=10,
             ast=30, stl=5, blk=2, three_pm=20, turnovers=5,
             fgm=6, fga=10, ftm=8, fta=10, team_wins=None),
        dict(player_id=2, full_name="High Volume", pts=200, reb=20,
             ast=20, stl=10, blk=4, three_pm=10, turnovers=15,
             fgm=60, fga=100, ftm=80, fta=100, team_wins=None),
        dict(player_id=3, full_name="Below Average", pts=150, reb=30,
             ast=10, stl=15, blk=6, three_pm=30, turnovers=25,
             fgm=40, fga=100, ftm=40, fta=100, team_wins=None),
    ])


def row_for(ranking: pd.DataFrame, player_id: int) -> pd.Series:
    return ranking.loc[ranking["player_id"] == player_id].iloc[0]


def test_nine_categories_exclude_team_wins():
    ranking = calculate_rankings(projections())
    assert len(SCORE_COLUMNS) == 9
    assert all(not name.startswith("z_tw") for name in ranking.columns)
    assert ranking["categories_available"].tolist() == [9, 9, 9]
    assert ranking["rank"].notna().all()


def test_turnovers_are_inverted():
    ranking = calculate_rankings(projections())
    assert row_for(ranking, 1)["z_to"] > row_for(ranking, 2)["z_to"]
    assert row_for(ranking, 2)["z_to"] > row_for(ranking, 3)["z_to"]


def test_fg_and_ft_scores_account_for_attempt_volume():
    ranking = calculate_rankings(projections())
    low = row_for(ranking, 1)
    high = row_for(ranking, 2)
    assert low["fg_pct"] == pytest.approx(high["fg_pct"])
    assert low["ft_pct"] == pytest.approx(high["ft_pct"])
    assert high["z_fg_pct"] > low["z_fg_pct"]
    assert high["z_ft_pct"] > low["z_ft_pct"]


def test_missing_projection_never_turns_into_zero():
    frame = projections()
    frame.loc[0, "pts"] = None
    ranking = calculate_rankings(frame)
    incomplete = row_for(ranking, 1)
    assert pd.isna(incomplete["z_pts"])
    assert incomplete["categories_available"] == 8
    assert "PTS" in incomplete["missing_categories"]
    assert pd.isna(incomplete["z_total"])
    assert pd.isna(incomplete["rank"])


def test_constant_category_prevents_false_full_ranking():
    frame = projections()
    frame["turnovers"] = 10
    ranking = calculate_rankings(frame)
    assert ranking["z_to"].isna().all()
    assert ranking["z_total"].isna().all()
    assert ranking["missing_categories"].str.contains("TO").all()


def test_invalid_shooting_counts_are_rejected():
    frame = projections()
    frame.loc[0, "fgm"] = 11
    with pytest.raises(ValueError, match="fgm/fga"):
        calculate_rankings(frame)


def test_sqlite_source_round_trip(tmp_path):
    db_path = tmp_path / "ranking.sqlite3"
    initialize_database(db_path)
    with get_connection(db_path) as connection:
        for player in projections().to_dict(orient="records"):
            player_id = player["player_id"]
            connection.execute(
                "INSERT INTO players(id, full_name, nba_team) VALUES (?, ?, ?)",
                (player_id, player["full_name"], "DEM"),
            )
            connection.execute(
                """INSERT INTO projections (
                    player_id, season, source, is_demo, pts, reb, ast, stl,
                    blk, three_pm, fgm, fga, ftm, fta, turnovers
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (player_id, "2026/27", "ranking_test", 1,
                 *(player[column] for column in (
                     "pts", "reb", "ast", "stl", "blk", "three_pm",
                     "fgm", "fga", "ftm", "fta", "turnovers"
                 ))),
            )
    ranking = load_rankings("ranking_test", db_path=db_path)
    assert len(ranking) == 3
    assert ranking["team_wins"].isna().all()
    assert ranking["rank"].notna().all()
    assert ranking["z_total"].is_monotonic_decreasing


def test_empty_source_returns_empty_rankings(tmp_path):
    db_path = tmp_path / "ranking.sqlite3"
    initialize_database(db_path)
    ranking = load_rankings("does_not_exist", db_path=db_path)
    assert ranking.empty
    assert "z_total" in ranking.columns
    assert "rank" in ranking.columns


def test_team_wins_never_changes_the_ranking():
    frame = projections()
    original = calculate_rankings(frame)
    frame["team_wins"] = [0, 70, 100]
    with_tw = calculate_rankings(frame)
    assert original["player_id"].tolist() == with_tw["player_id"].tolist()
    assert original["z_total"].tolist() == pytest.approx(
        with_tw["z_total"].tolist()
    )


def test_zero_attempts_do_not_create_fictitious_percentage():
    frame = projections()
    frame.loc[0, ["fgm", "fga", "ftm", "fta"]] = 0
    ranking = calculate_rankings(frame)
    player = row_for(ranking, 1)
    assert pd.isna(player["fg_pct"])
    assert pd.isna(player["z_fg_pct"])
    assert pd.isna(player["ft_pct"])
    assert pd.isna(player["z_ft_pct"])
    assert "FG%" in player["missing_categories"]
    assert "FT%" in player["missing_categories"]
    assert pd.isna(player["z_total"])
