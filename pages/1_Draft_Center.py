
"""Import i przeglądanie prognoz zawodników w Draft Center."""

from pathlib import Path

import pandas as pd
import streamlit as st

from nba_fantasy_lab.database import DEFAULT_DB_PATH, get_connection, initialize_database
from nba_fantasy_lab.importer import SEASON, import_projections
from nba_fantasy_lab.stat_views import PER_GAME_LABELS, convert_to_per_game

DEMO_FILE = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "demo_projections.csv"
)

st.set_page_config(
    page_title="Draft Center | NBA Fantasy Lab",
    page_icon="🏀",
    layout="wide",
)

initialize_database()

st.title("🏀 Draft Center")
st.caption(
    "Etap 4: import CSV, wyszukiwanie, filtrowanie "
    "i sortowanie prognoz sezonowych."
)
st.warning(
    "TW: wzór ESPN niezweryfikowany. "
    "Brak prognozy oznacza brak danych, nie zero."
)

with st.expander("Import prognoz CSV", expanded=True):
    st.info(
        "Plik przykładowy jest DEMONSTRACYJNY: fikcyjni zawodnicy "
        "i wymyślone statystyki. Nie używaj go do rzeczywistego draftu."
    )

    if st.button("Zaimportuj demo_projections.csv"):
        try:
            count = import_projections(
                DEMO_FILE.read_bytes(),
                source="demo_phase01",
                is_demo=True,
                db_path=DEFAULT_DB_PATH,
            )
            st.success(
                f"Zaimportowano {count} wierszy demonstracyjnych do SQLite."
            )
        except (ValueError, OSError) as exc:
            st.error(f"Import nieudany: {exc}")

    upload = st.file_uploader(
        "Albo wybierz własny plik CSV (UTF-8)",
        type=["csv"],
    )
    source = st.text_input(
        "Identyfikator źródła importu",
        value="user_csv",
    )
    demo = st.checkbox(
        "Wgrywany plik zawiera dane demonstracyjne",
        value=False,
    )

    if st.button("Importuj przesłany plik", disabled=upload is None):
        try:
            count = import_projections(
                upload.getvalue(),
                source=source,
                is_demo=demo,
                db_path=DEFAULT_DB_PATH,
            )
            st.success(
                f"Zapisano {count} wierszy prognoz do SQLite."
            )
        except ValueError as exc:
            st.error(f"CSV: {exc}")

    st.caption(
        "Wymagane kolumny: full_name, nba_team, positions "
        "(np. PG|SG). Opcjonalne: games, pts, reb, ast, "
        "stl, blk, three_pm, fgm, fga, ftm, fta, "
        "turnovers, team_wins."
    )

with get_connection() as connection:
    source_rows = connection.execute(
        "SELECT source, MAX(is_demo) AS is_demo, "
        "COUNT(*) AS total "
        "FROM projections WHERE season = ? "
        "GROUP BY source ORDER BY source",
        (SEASON,),
    ).fetchall()

if not source_rows:
    st.info("Brak prognoz w bazie. Zaimportuj plik CSV powyżej.")
    st.stop()

sources = {
    row["source"]: bool(row["is_demo"])
    for row in source_rows
}
selected_source = st.selectbox(
    "Źródło prognoz",
    list(sources),
)

if sources[selected_source]:
    st.warning(
        "Wyświetlane są DANE DEMONSTRACYJNE — "
        "nie prognozy rzeczywistych graczy."
    )

with get_connection() as connection:
    df = pd.read_sql_query(
        """
        SELECT p.full_name AS "Zawodnik",
               p.nba_team AS "Zespół",
               (SELECT GROUP_CONCAT(pos.code, '/')
                FROM player_positions pp
                JOIN positions pos ON pos.id = pp.position_id
                WHERE pp.player_id = p.id) AS "Pozycje",
               pr.games AS "Mecze",
               pr.pts AS "PTS",
               pr.reb AS "REB",
               pr.ast AS "AST",
               pr.stl AS "STL",
               pr.blk AS "BLK",
               pr.three_pm AS "3PM",
               pr.fgm AS "FGM",
               pr.fga AS "FGA",
               pr.ftm AS "FTM",
               pr.fta AS "FTA",
               pr.turnovers AS "TO",
               pr.team_wins AS "TW"
        FROM projections pr
        JOIN players p ON p.id = pr.player_id
        WHERE pr.season = ? AND pr.source = ?
        ORDER BY p.full_name
        """,
        connection,
        params=(SEASON, selected_source),
    )

numeric_columns = [
    "Mecze", "PTS", "REB", "AST", "STL", "BLK",
    "3PM", "FGM", "FGA", "FTM", "FTA", "TO", "TW",
]
for column in numeric_columns:
    df[column] = pd.to_numeric(df[column], errors="coerce")

df["FG%"] = (
    100 * df["FGM"] / df["FGA"]
).where(df["FGA"] > 0)

df["FT%"] = (
    100 * df["FTM"] / df["FTA"]
).where(df["FTA"] > 0)

# Switch the table view without modifying SQLite or Z-score calculations.
stat_view = st.radio(
    "Widok statystyk",
    ("Średnie na mecz", "Sumy sezonowe"),
    horizontal=True,
    key="projection_stat_view",
)
per_game = stat_view == "Średnie na mecz"
if per_game:
    df = convert_to_per_game(df)

search_col, pos_col, sort_col, direction_col = st.columns(
    [3, 2, 2, 1]
)

with search_col:
    search = st.text_input(
        "Szukaj zawodnika",
        placeholder="Wpisz nazwisko lub nazwę...",
    )

with pos_col:
    position = st.selectbox(
        "Pozycja",
        ["Wszystkie", "PG", "SG", "SF", "PF", "C"],
    )

with sort_col:
    sort_by = st.selectbox(
        "Sortuj według",
        [
            "Zawodnik", "PTS", "REB", "AST", "STL",
            "BLK", "3PM", "FG%", "FT%", "TO",
        ],
        format_func=lambda column: (
            PER_GAME_LABELS.get(column, column) if per_game else column
        ),
    )

with direction_col:
    ascending = st.checkbox(
        "Rosnąco",
        value=False,
    )

if search.strip():
    df = df[
        df["Zawodnik"].str.contains(
            search.strip(),
            case=False,
            regex=False,
            na=False,
        )
    ]

if position != "Wszystkie":
    df = df[
        df["Pozycje"]
        .fillna("")
        .str.split("/")
        .apply(lambda values: position in values)
    ]

df = df.sort_values(
    sort_by,
    ascending=ascending,
    na_position="last",
)

st.metric("Zawodnicy w widoku", len(df))


# Select the columns to display in the player table.
display_columns = [
    "Zawodnik", "Zespół", "Pozycje", "Mecze",
    "PTS", "REB", "AST", "STL", "BLK", "3PM",
    "FG%", "FT%", "TO", "TW",
]

display_df = df[display_columns].copy()
if per_game:
    display_df = display_df.rename(columns=PER_GAME_LABELS)
    display_df = display_df.round(2)

# Paginate results to keep large player lists responsive.
page_size = st.selectbox(
    "Zawodników na stronę",
    [25, 50, 100],
    index=0,
)

total_pages = max(
    1,
    (len(display_df) + page_size - 1) // page_size,
)

page_number = st.selectbox(
    "Strona tabeli",
    list(range(1, total_pages + 1)),
)

start = (page_number - 1) * page_size
page_df = display_df.iloc[start:start + page_size]

# Generate HTML without requiring PyArrow.
# All player data is HTML-escaped before rendering.
table_html = page_df.to_html(
    index=False,
    escape=True,
    border=0,
    na_rep="—",
    classes="fantasy-table",
    formatters={
        "FG%": lambda value: f"{value:.1f}%",
        "FT%": lambda value: f"{value:.1f}%",
    },
)

st.markdown(
    """
    <style>
    .fantasy-table-wrapper {
        overflow-x: auto;
        width: 100%;
    }
    .fantasy-table {
        border-collapse: collapse;
        width: 100%;
        font-size: 0.9rem;
    }
    .fantasy-table th,
    .fantasy-table td {
        padding: 10px 14px;
        border-bottom: 1px solid #5555;
        text-align: left;
        white-space: nowrap;
    }
    .fantasy-table th {
        font-weight: 700;
        border-bottom: 2px solid #8888;
    }
    .fantasy-table tbody tr:hover {
        background: #8882;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    f'<div class="fantasy-table-wrapper">{table_html}</div>',
    unsafe_allow_html=True,
)

st.caption(
    ("Statystyki: średnie na mecz. " if per_game
     else "Statystyki: sumy sezonowe. ")
    + "Brakujące prognozy pozostają puste (—). "
    + "Ranking Z-score nadal bazuje na sumach sezonowych. "
    + "Live Draft znajduje się poniżej."
)

# Render persisted draft controls below the projections browser.
from nba_fantasy_lab.draft_ui import render_draft_center
render_draft_center(selected_source)
