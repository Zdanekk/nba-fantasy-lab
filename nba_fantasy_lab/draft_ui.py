"""Streamlit controls for persisted snake draft sessions and ranked players.

Do not use st.dataframe or st.table: this Windows setup blocks PyArrow DLLs.
"""

import sqlite3

import pandas as pd
import streamlit as st

from nba_fantasy_lab.database import DEFAULT_DB_PATH
from nba_fantasy_lab.i18n import column_label, t
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


def _show_html_table(frame: pd.DataFrame) -> None:
    """Render an escaped HTML table, avoiding Streamlit's Arrow serializer."""
    if frame.empty:
        st.info(t("draft.empty_table"))
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
    with st.expander(t("draft.new"), expanded=False):
        with st.form("new_draft_session_form"):
            name = st.text_input(t("draft.session_name"), value="Draft 2026/27")
            teams_text = st.text_area(
                t("draft.teams_input"),
                value="\n".join(t("draft.default_team", number=f"{i:02d}") for i in range(1, 13)),
                height=290,
            )
            submitted = st.form_submit_button(t("draft.create"))
        if submitted:
            try:
                session_id = create_draft_session(
                    name, teams_text.splitlines(), db_path=DEFAULT_DB_PATH
                )
            except (DraftError, sqlite3.IntegrityError) as exc:
                st.error(t("draft.create_error", error=exc))
            else:
                st.session_state["fantasy_draft_session_id"] = session_id
                st.session_state["fantasy_draft_session_choice"] = session_id
                st.session_state["fantasy_draft_notice"] = t("draft.created")
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
    with st.expander(t("draft.edit_order")):
        st.caption(t("draft.edit_hint"))
        draft_order = st.text_area(
            t("draft.order"), value="\n".join(team_names),
            height=285, key=f"fantasy_draft_order_{session_id}",
        )
        if st.button(t("draft.save_order"), key=f"save_order_{session_id}"):
            try:
                set_draft_order(
                    session_id, draft_order.splitlines(), db_path=DEFAULT_DB_PATH
                )
            except (DraftError, sqlite3.IntegrityError) as exc:
                st.error(t("draft.save_error", error=exc))
            else:
                st.session_state["fantasy_draft_notice"] = t("draft.order_saved")
                st.rerun()


def _player_board(session_id: int, source: str, state: dict) -> None:
    """Show only undrafted source players and record the next snake pick."""
    board = available_rankings(session_id, source, db_path=DEFAULT_DB_PATH)
    search_col, position_col = st.columns([3, 1])
    with search_col:
        query = st.text_input(t("draft.search"), key="draft_search")
    with position_col:
        position = st.selectbox(
            t("draft.position"), ["Wszystkie", "PG", "SG", "SF", "PF", "C"],
            format_func=lambda choice: (t("filter.all") if choice == "Wszystkie" else choice),
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

    st.metric(t("draft.available_count"), len(board))
    if board.empty:
        st.info(t("draft.no_available"))
        return

    display = board[[
        "full_name", "nba_team", "positions", "rank", "z_total",
        "categories_available", "missing_categories",
    ]].copy()
    display.columns = [
        t("table.player"), t("table.team"), t("table.positions"),
        t("draft.rank"), t("draft.zscore"),
        t("draft.categories_available"), t("draft.categories_missing"),
    ]
    display[t("draft.zscore")] = display[t("draft.zscore")].round(2)
    _show_html_table(display.head(50))
    if len(board) > 50:
        st.caption(t("draft.show_50"))

    if board["z_total"].isna().any():
        st.warning(t("draft.incomplete"))

    if state["next_turn"] is None:
        return

    # The selectbox uses immutable player IDs, not names, to avoid ambiguity.
    labels = {
        int(row.player_id): row.full_name
        for row in board[["player_id", "full_name"]].itertuples(index=False)
    }
    with st.form(f"draft_pick_form_{session_id}"):
        player_id = st.selectbox(
            t("draft.player_select"),
            options=list(labels),
            format_func=lambda value: labels[value],
        )
        submitted = st.form_submit_button(t("draft.save_pick"))

    if submitted:
        try:
            turn = make_pick(session_id, int(player_id), db_path=DEFAULT_DB_PATH)
        except (DraftError, sqlite3.IntegrityError) as exc:
            st.error(t("draft.pick_error", error=exc))
        else:
            st.session_state["fantasy_draft_notice"] = (
                t("draft.pick_saved", number=turn.overall_pick, player=labels[player_id])
            )
            st.rerun()


def render_draft_center(source: str) -> None:
    """Add persistent draft controls beneath the existing projections browser."""
    st.divider()
    st.header(t("draft.heading"))
    st.caption(t("draft.description"))
    notice = st.session_state.pop("fantasy_draft_notice", None)
    if notice:
        st.success(notice)

    _create_session()
    sessions = list_sessions(db_path=DEFAULT_DB_PATH)
    if not sessions:
        st.info(t("draft.no_sessions"))
        return

    session_labels = {
        session["id"]: f'#{session["id"]} · {session["name"]} ({t("draft.status." + session["status"])})'
        for session in sessions
    }
    current_id = st.session_state.get("fantasy_draft_session_id")
    if current_id not in session_labels:
        current_id = sessions[0]["id"]

    session_id = st.selectbox(
        t("draft.session"),
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

    st.write(t("draft.progress", done=state["completed_picks"], total=state["total_picks"]))
    if state["next_turn"] is not None:
        turn = state["next_turn"]
        st.info(t("draft.on_clock", team=state["next_team"],
                  number=turn.overall_pick, round=turn.round_number,
                  slot=turn.draft_slot))
    else:
        st.success(t("draft.finished"))

    with st.expander(t("draft.teams_heading"), expanded=False):
        _show_html_table(pd.DataFrame([
            {t("draft.slot"): slot, t("draft.team"): team["team_name"]}
            for slot, team in state["teams"].items()
        ]))
    _edit_order(state)

    st.subheader(t("draft.available"))
    try:
        _player_board(session_id, source, state)
    except (DraftError, ValueError) as exc:
        st.error(t("draft.available_error", error=exc))

    picks = list_draft_picks(session_id, db_path=DEFAULT_DB_PATH)
    st.subheader(t("draft.picks"))
    if picks:
        view = pd.DataFrame(picks)[[
            "overall_pick", "round_number", "draft_slot", "team_name", "full_name"
        ]]
        view.columns = [t("draft.number"), t("draft.round"), t("draft.slot"),
                        t("draft.team"), t("draft.player")]
        _show_html_table(view.tail(30))
    else:
        st.info(t("draft.no_picks"))

    events = list_pick_events(session_id, db_path=DEFAULT_DB_PATH)
    if picks:
        st.caption(t("draft.undo_hint"))
        confirm = st.checkbox(
            t("draft.undo_confirm"),
            key=f"undo_confirm_{session_id}_{len(events)}",
        )
        if st.button(t("draft.undo_button"), disabled=not confirm):
            try:
                undo_last_pick(session_id, db_path=DEFAULT_DB_PATH)
            except (DraftError, sqlite3.IntegrityError) as exc:
                st.error(t("draft.undo_error", error=exc))
            else:
                st.session_state["fantasy_draft_notice"] = t("draft.undo_success")
                st.rerun()

    with st.expander(t("draft.events"), expanded=False):
        if events:
            audit = pd.DataFrame(events)[[
                "created_at", "overall_pick", "event_type", "full_name"
            ]]
            audit.columns = [t("draft.time"), t("draft.number"),
                         t("draft.event"), t("draft.player")]
            audit[t("draft.event")] = audit[t("draft.event")].map(
                lambda code: t("draft.event." + code)
            )
            _show_html_table(audit.tail(50))
        else:
            st.caption(t("draft.no_events"))

    st.caption(t("draft.limits"))
