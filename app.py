
"""Home page of the multipage Streamlit application."""

import streamlit as st

from nba_fantasy_lab.database import get_connection, initialize_database
from nba_fantasy_lab.i18n import language_selector, t

st.set_page_config(
    page_title="NBA Fantasy Lab",
    page_icon="🏀",
    layout="wide",
)

language_selector()
initialize_database()

st.title("🏀 NBA Fantasy Lab")
st.subheader(t("home.subtitle"))
st.info(t("home.choose"))

with get_connection() as connection:
    players = connection.execute(
        "SELECT COUNT(*) FROM players"
    ).fetchone()[0]
    projections = connection.execute(
        "SELECT COUNT(*) FROM projections"
    ).fetchone()[0]

col1, col2 = st.columns(2)
col1.metric(t("home.players"), players)
col2.metric(t("home.projections"), projections)

st.warning(t("home.demo_warning"))

st.caption(t("home.footer"))
