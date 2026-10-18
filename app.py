
"""Strona główna wielostronicowej aplikacji Streamlit."""

import streamlit as st

from nba_fantasy_lab.database import get_connection, initialize_database

st.set_page_config(
    page_title="NBA Fantasy Lab",
    page_icon="🏀",
    layout="wide",
)

initialize_database()

st.title("🏀 NBA Fantasy Lab")
st.subheader("Koszobidon Fantasy · Sezon 2026/27")
st.info("Wybierz Draft Center w menu po lewej stronie.")

with get_connection() as connection:
    players = connection.execute(
        "SELECT COUNT(*) FROM players"
    ).fetchone()[0]
    projections = connection.execute(
        "SELECT COUNT(*) FROM projections"
    ).fetchone()[0]

col1, col2 = st.columns(2)
col1.metric("Zawodnicy w bazie", players)
col2.metric("Rekordy prognoz", projections)

st.warning(
    "Dane demonstracyjne nie są prawdziwymi prognozami NBA. "
    "Zasada punktowania Team Wins (TW) wymaga jeszcze weryfikacji w ESPN."
)

st.caption(
    "Faza 01 · Lokalna aplikacja · SQLite · Bez integracji z ESPN"
)
