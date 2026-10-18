"""Streamlit controls for persisted snake draft sessions and ranked players.

Do not use st.dataframe or st.table: this Windows setup blocks PyArrow DLLs.
"""

import sqlite3

import pandas as pd
import streamlit as st

from nba_fantasy_lab.database import DEFAULT_DB_PATH
from nba_fantasy_lab.draft_engine import (
    DraftError,
    create_draft_session,
    get_draft_state,
    list_draft_picks,
    list_pick_events,
    make_pick,
    set_draft_order,
    undo_last_pick,
)
from nba_fantasy_lab.draft_view import available_rankings, list_sessions


DEFAULT_TEAM_NAMES = "\n".join(f"Drużyna {index:02d}" for index in range(1, 13))


def _show_html_table(frame: pd.DataFrame) -> None:
    """Render an escaped HTML table, avoiding Streamlit's Arrow serializer."""
    if frame.empty:
        st.info("Brak danych do wyświetlenia.")
        return

    html = frame.to_html(
        index=False,
        escape=True,
        border=0,
        na_rep="—",
        classes="fantasy-table",
    )
    st.markdown(
        """<style>
        .draft-table-container { width: 100%; overflow-x: auto; }
        .draft-table-container table { width: 100%; border-collapse: collapse; }
        .draft-table-container th, .draft-table-container td {
            padding: 9px 12px; text-align: left;
            border-bottom: 1px solid #8885; white-space: nowrap;
        }
        </style>""",
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="draft-table-container">{html}</div>',
        unsafe_allow_html=True,
    )


def _create_session() -> None:
    """Create an independent draft session with an ordered set of 12 teams."""
    with st.expander("Nowa sesja draftu", expanded=False):
        with st.form("new_draft_session_form"):
            name = st.text_input("Nazwa sesji", value="Draft 2026/27")
            teams_text = st.text_area(
                "12 drużyn — jedna w każdym wierszu, w kolejności draftu",
                value=DEFAULT_TEAM_NAMES,
                height=290,
            )
            submitted = st.form_submit_button("Utwórz sesję")
        if submitted:
            try:
                session_id = create_draft_session(
                    name, teams_text.splitlines(), db_path=DEFAULT_DB_PATH
                )
            except (DraftError, sqlite3.IntegrityError) as exc:
                st.error(f"Nie udało się utworzyć sesji: {exc}")
            else:
                st.session_state["fantasy_draft_session_id"] = session_id
                st.session_state["fantasy_draft_session_choice"] = session_id
                st.session_state["fantasy_draft_notice"] = "Utworzono sesję draftu."
                st.rerun()


def _edit_order(state: dict) -> None:
    """Allow changing draft order only while the engine permits it."""
    if state["status"] != "setup":
        return
    session_id = state["session_id"]
    team_names = [
        state["teams"][index]["team_name"]
        for index in range(1, len(state["teams"]) + 1)
    ]
    with st.expander("Zmień kolejność drużyn — tylko przed pierwszym wyborem"):
        st.caption("Przestaw wiersze, aby określić kolejność slotów 1–12.")
        draft_order = st.text_area(
            "Kolejność drużyn", value="\n".join(team_names),
            height=285, key=f"fantasy_draft_order_{session_id}",
        )
        if st.button("Zapisz kolejność", key=f"save_order_{session_id}"):
            try:
                set_draft_order(
                    session_id, draft_order.splitlines(), db_path=DEFAULT_DB_PATH
                )
            except (DraftError, sqlite3.IntegrityError) as exc:
                st.error(f"Nie udało się zmienić kolejności: {exc}")
            else:
                st.session_state["fantasy_draft_notice"] = "Zapisano kolejność drużyn."
                st.rerun()


def _player_board(session_id: int, source: str, state: dict) -> None:
    """Show only undrafted source players and record the next snake pick."""
    board = available_rankings(session_id, source, db_path=DEFAULT_DB_PATH)
    search_col, position_col = st.columns([3, 1])
    with search_col:
        query = st.text_input("Szukaj dostępnego zawodnika", key="draft_search")
    with position_col:
        position = st.selectbox(
            "Pozycja dostępnych", ["Wszystkie", "PG", "SG", "SF", "PF", "C"],
            key="draft_position",
        )
    if query.strip():
        board = board.loc[
            board["full_name"].str.contains(
                query.strip(), case=False, regex=False, na=False
            )
        ]
    if position != "Wszystkie":
        board = board.loc[
            board["positions"].str.split("/").apply(
                lambda codes: position in codes
            )
        ]

    st.metric("Dostępni zawodnicy w widoku", len(board))
    if board.empty:
        st.info(
            "Brak dostępnych zawodników dla aktualnych filtrów lub źródła. "
            "Możesz zmienić filtry albo zaimportować dodatkowe prognozy."
        )
        return

    display = board[[
        "full_name", "nba_team", "positions", "rank", "z_total",
        "categories_available", "missing_categories",
    ]].copy()
    display.columns = [
        "Zawodnik", "Zespół", "Pozycje", "Ranking", "Z-score (9 kat.)",
        "Dostępne kategorie", "Brakujące kategorie",
    ]
    display["Z-score (9 kat.)"] = display["Z-score (9 kat.)"].round(2)
    _show_html_table(display.head(50))
    if len(board) > 50:
        st.caption("Wyświetlono pierwszych 50 zawodników. Zawęź listę wyszukiwarką.")

    if board["z_total"].isna().any():
        st.warning("Niektóre prognozy są niepełne — brak pełnego rankingu Z-score.")

    if state["next_turn"] is None:
        return

    # The selectbox uses immutable player IDs, not names, to avoid ambiguity.
    labels = {
        int(row.player_id): row.full_name
        for row in board[["player_id", "full_name"]].itertuples(index=False)
    }
    with st.form(f"draft_pick_form_{session_id}"):
        player_id = st.selectbox(
            "Zawodnik do wybrania",
            options=list(labels),
            format_func=lambda value: labels[value],
        )
        submitted = st.form_submit_button("Zapisz następny wybór")

    if submitted:
        try:
            turn = make_pick(session_id, int(player_id), db_path=DEFAULT_DB_PATH)
        except (DraftError, sqlite3.IntegrityError) as exc:
            st.error(f"Nie udało się zapisać wyboru: {exc}")
        else:
            st.session_state["fantasy_draft_notice"] = (
                f"Wybór #{turn.overall_pick}: {labels[player_id]} zapisany w SQLite."
            )
            st.rerun()


def render_draft_center(source: str) -> None:
    """Add persistent draft controls beneath the existing projections browser."""
    st.divider()
    st.header("🏀 Live Draft — sesje, wybory i ranking")
    st.caption(
        "Ranking liczony względem pełnego zbioru prognoz danego źródła. "
        "Zawodnicy wybrani znikają z poniższej listy dostępnych. "
        "TW pozostaje wyłączone z rankingu."
    )
    notice = st.session_state.pop("fantasy_draft_notice", None)
    if notice:
        st.success(notice)

    _create_session()
    sessions = list_sessions(db_path=DEFAULT_DB_PATH)
    if not sessions:
        st.info("Brak sesji draftowych. Utwórz nową sesję powyżej.")
        return

    session_labels = {
        session["id"]: f'#{session["id"]} · {session["name"]} ({session["status"]})'
        for session in sessions
    }
    current_id = st.session_state.get("fantasy_draft_session_id")
    if current_id not in session_labels:
        current_id = sessions[0]["id"]

    session_id = st.selectbox(
        "Sesja draftowa",
        options=list(session_labels),
        index=list(session_labels).index(current_id),
        format_func=lambda value: session_labels[value],
        key="fantasy_draft_session_choice",
    )
    st.session_state["fantasy_draft_session_id"] = session_id
    try:
        state = get_draft_state(session_id, db_path=DEFAULT_DB_PATH)
    except DraftError as exc:
        st.error(str(exc))
        return

    st.write(f'**Postęp:** {state["completed_picks"]}/{state["total_picks"]} wyborów')
    if state["next_turn"] is not None:
        turn = state["next_turn"]
        st.info(
            f'Na zegarze: **{state["next_team"]}** · '
            f'wybór **#{turn.overall_pick}** · '
            f'runda **{turn.round_number}** · slot **{turn.draft_slot}**'
        )
    else:
        st.success("Draft zakończony: wszystkie 156 wyborów zostały zapisane.")

    with st.expander("Kolejność 12 drużyn", expanded=False):
        _show_html_table(pd.DataFrame([
            {"Slot": slot, "Drużyna": team["team_name"]}
            for slot, team in state["teams"].items()
        ]))
    _edit_order(state)

    st.subheader("Dostępni zawodnicy")
    try:
        _player_board(session_id, source, state)
    except (DraftError, ValueError) as exc:
        st.error(f"Nie udało się wczytać listy zawodników: {exc}")

    picks = list_draft_picks(session_id, db_path=DEFAULT_DB_PATH)
    st.subheader("Historia aktywnych wyborów")
    if picks:
        view = pd.DataFrame(picks)[[
            "overall_pick", "round_number", "draft_slot", "team_name", "full_name"
        ]]
        view.columns = ["Numer", "Runda", "Slot", "Drużyna", "Zawodnik"]
        _show_html_table(view.tail(30))
    else:
        st.info("Nie zarejestrowano jeszcze żadnego wyboru.")

    events = list_pick_events(session_id, db_path=DEFAULT_DB_PATH)
    if picks:
        st.caption("Możesz cofnąć wyłącznie ostatni wybór.")
        confirm = st.checkbox(
            "Potwierdzam cofnięcie ostatniego wyboru",
            key=f"undo_confirm_{session_id}_{len(events)}",
        )
        if st.button("Cofnij ostatni wybór", disabled=not confirm):
            try:
                undo_last_pick(session_id, db_path=DEFAULT_DB_PATH)
            except (DraftError, sqlite3.IntegrityError) as exc:
                st.error(f"Nie udało się cofnąć wyboru: {exc}")
            else:
                st.session_state["fantasy_draft_notice"] = "Ostatni wybór cofnięty."
                st.rerun()

    with st.expander("Dziennik zdarzeń — wybory i cofnięcia", expanded=False):
        if events:
            audit = pd.DataFrame(events)[[
                "created_at", "overall_pick", "event_type", "full_name"
            ]]
            audit.columns = ["Czas", "Numer", "Zdarzenie", "Zawodnik"]
            _show_html_table(audit.tail(50))
        else:
            st.caption("Dziennik jest pusty.")

    st.caption(
        "Limit czasu wyboru (90 s) nie jest jeszcze odmierzany. "
        "Dane demonstracyjne zawierają tylko 12 zawodników, "
        "więc pełne 156 wyborów wymaga większego CSV."
    )
