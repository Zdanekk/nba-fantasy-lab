"""Centralized Polish and English UI strings for NBA Fantasy Lab.

All stored values, database identifiers, statistics, and draft logic are language-neutral.
"""

from __future__ import annotations

LANGUAGES = ("pl", "en")
DEFAULT_LANGUAGE = "pl"

TEXT = {
    "pl": {
        "home.subtitle": "Koszobidon Fantasy · Sezon 2026/27",
        "home.choose": "Wybierz Draft Center w menu po lewej stronie.",
        "home.players": "Zawodnicy w bazie",
        "home.projections": "Rekordy prognoz",
        "home.demo_warning": "Dane demonstracyjne nie są prawdziwymi prognozami NBA. Zasada punktowania Team Wins (TW) wymaga jeszcze weryfikacji w ESPN.",
        "home.footer": "Faza 01 · Lokalna aplikacja · SQLite · Bez integracji z ESPN",
        "page.intro": "Import CSV, wyszukiwanie, filtrowanie i sortowanie prognoz sezonowych.",
        "page.tw_warning": "TW: wzór ESPN niezweryfikowany. Brak prognozy oznacza brak danych, nie zero.",
        "import.header": "Import prognoz CSV",
        "import.demo_notice": "Plik przykładowy jest DEMONSTRACYJNY: fikcyjni zawodnicy i wymyślone statystyki. Nie używaj go do rzeczywistego draftu.",
        "import.demo_button": "Zaimportuj demo_projections.csv",
        "import.demo_success": "Zaimportowano {count} wierszy demonstracyjnych do SQLite.",
        "import.error": "Import nieudany: {error}",
        "import.upload": "Albo wybierz własny plik CSV (UTF-8)",
        "import.source_id": "Identyfikator źródła importu",
        "import.is_demo": "Wgrywany plik zawiera dane demonstracyjne",
        "import.upload_button": "Importuj przesłany plik",
        "import.upload_success": "Zapisano {count} wierszy prognoz do SQLite.",
        "import.columns": "Wymagane kolumny: full_name, nba_team, positions (np. PG|SG). Opcjonalne: games, pts, reb, ast, stl, blk, three_pm, fgm, fga, ftm, fta, turnovers, team_wins.",
        "import.no_source": "Brak prognoz w bazie. Zaimportuj plik CSV powyżej.",
        "import.source": "Źródło prognoz",
        "import.demo_active": "Wyświetlane są DANE DEMONSTRACYJNE — nie prognozy rzeczywistych graczy.",
        "filter.search": "Szukaj zawodnika",
        "filter.placeholder": "Wpisz nazwisko lub nazwę...",
        "filter.position": "Pozycja",
        "filter.all": "Wszystkie",
        "filter.sort": "Sortuj według",
        "filter.asc": "Rosnąco",
        "filter.total": "Zawodnicy w widoku",
        "table.page_size": "Zawodników na stronę",
        "table.page": "Strona tabeli",
        "table.player": "Zawodnik",
        "table.team": "Zespół",
        "table.positions": "Pozycje",
        "table.games": "Mecze",
        "table.note_per_game": "Statystyki: średnie na mecz. Brakujące prognozy pozostają puste (—). Ranking Z-score nadal bazuje na sumach sezonowych. Live Draft znajduje się poniżej.",
        "table.note_season": "Statystyki: sumy sezonowe. Brakujące prognozy pozostają puste (—). Ranking Z-score nadal bazuje na sumach sezonowych. Live Draft znajduje się poniżej.",
        "stats.label": "Widok statystyk",
        "stats.per_game": "Średnie na mecz",
        "stats.season": "Sumy sezonowe",
        "draft.empty_table": "Brak danych do wyświetlenia.",
        "draft.new": "Nowa sesja draftu",
        "draft.session_name": "Nazwa sesji",
        "draft.teams_input": "12 drużyn — jedna w każdym wierszu, w kolejności draftu",
        "draft.default_team": "Drużyna {number}",
        "draft.create": "Utwórz sesję",
        "draft.create_error": "Nie udało się utworzyć sesji: {error}",
        "draft.created": "Utworzono sesję draftu.",
        "draft.edit_order": "Zmień kolejność drużyn — tylko przed pierwszym wyborem",
        "draft.edit_hint": "Przestaw wiersze, aby określić kolejność slotów 1–12.",
        "draft.order": "Kolejność drużyn",
        "draft.save_order": "Zapisz kolejność",
        "draft.save_error": "Nie udało się zmienić kolejności: {error}",
        "draft.order_saved": "Zapisano kolejność drużyn.",
        "draft.search": "Szukaj dostępnego zawodnika",
        "draft.position": "Pozycja dostępnych",
        "draft.available_count": "Dostępni zawodnicy w widoku",
        "draft.no_available": "Brak dostępnych zawodników dla aktualnych filtrów lub źródła. Możesz zmienić filtry albo zaimportować dodatkowe prognozy.",
        "draft.rank": "Ranking",
        "draft.zscore": "Z-score (9 kat.)",
        "draft.categories_available": "Dostępne kategorie",
        "draft.categories_missing": "Brakujące kategorie",
        "draft.show_50": "Wyświetlono pierwszych 50 zawodników. Zawęź listę wyszukiwarką.",
        "draft.incomplete": "Niektóre prognozy są niepełne — brak pełnego rankingu Z-score.",
        "draft.player_select": "Zawodnik do wybrania",
        "draft.save_pick": "Zapisz następny wybór",
        "draft.pick_error": "Nie udało się zapisać wyboru: {error}",
        "draft.pick_saved": "Wybór #{number}: {player} zapisany w SQLite.",
        "draft.heading": "🏀 Live Draft — sesje, wybory i ranking",
        "draft.description": "Ranking liczony względem pełnego zbioru prognoz danego źródła. Zawodnicy wybrani znikają z poniższej listy dostępnych. TW pozostaje wyłączone z rankingu.",
        "draft.no_sessions": "Brak sesji draftowych. Utwórz nową sesję powyżej.",
        "draft.session": "Sesja draftowa",
        "draft.progress": "**Postęp:** {done}/{total} wyborów",
        "draft.on_clock": "Na zegarze: **{team}** · wybór **#{number}** · runda **{round}** · slot **{slot}**",
        "draft.finished": "Draft zakończony: wszystkie 156 wyborów zostały zapisane.",
        "draft.teams_heading": "Kolejność 12 drużyn",
        "draft.slot": "Slot",
        "draft.team": "Drużyna",
        "draft.available": "Dostępni zawodnicy",
        "draft.available_error": "Nie udało się wczytać listy zawodników: {error}",
        "draft.picks": "Historia aktywnych wyborów",
        "draft.number": "Numer",
        "draft.round": "Runda",
        "draft.player": "Zawodnik",
        "draft.no_picks": "Nie zarejestrowano jeszcze żadnego wyboru.",
        "draft.undo_hint": "Możesz cofnąć wyłącznie ostatni wybór.",
        "draft.undo_confirm": "Potwierdzam cofnięcie ostatniego wyboru",
        "draft.undo_button": "Cofnij ostatni wybór",
        "draft.undo_error": "Nie udało się cofnąć wyboru: {error}",
        "draft.undo_success": "Ostatni wybór cofnięty.",
        "draft.events": "Dziennik zdarzeń — wybory i cofnięcia",
        "draft.time": "Czas",
        "draft.event": "Zdarzenie",
        "draft.no_events": "Dziennik jest pusty.",
        "draft.limits": "Limit czasu wyboru (90 s) nie jest jeszcze odmierzany. Dane demonstracyjne zawierają tylko 12 zawodników, więc pełne 156 wyborów wymaga większego CSV.",
        "draft.event.pick": "Wybór",
        "draft.event.undo": "Cofnięcie",
        "draft.status.setup": "Konfiguracja",
        "draft.status.in_progress": "W trakcie",
        "draft.status.finished": "Zakończony",
    },
    "en": {
        "home.subtitle": "Koszobidon Fantasy · Season 2026/27",
        "home.choose": "Choose Draft Center from the sidebar.",
        "home.players": "Players in database",
        "home.projections": "Projection records",
        "home.demo_warning": "Demo data is not real NBA projections. The ESPN Team Wins (TW) scoring rule still needs verification.",
        "home.footer": "Phase 01 · Local application · SQLite · No ESPN integration",
        "page.intro": "Import CSV files, search, filter, and sort season projections.",
        "page.tw_warning": "TW: ESPN scoring rule not verified. Missing projections mean missing data, not zero.",
        "import.header": "Import CSV projections",
        "import.demo_notice": "The sample file contains DEMO DATA: fictional players and statistics. Do not use it for a real draft.",
        "import.demo_button": "Import demo_projections.csv",
        "import.demo_success": "Imported {count} demo rows into SQLite.",
        "import.error": "Import failed: {error}",
        "import.upload": "Or upload your own CSV (UTF-8)",
        "import.source_id": "Import source identifier",
        "import.is_demo": "Uploaded file contains demo data",
        "import.upload_button": "Import uploaded file",
        "import.upload_success": "Saved {count} projection rows to SQLite.",
        "import.columns": "Required columns: full_name, nba_team, positions (e.g. PG|SG). Optional: games, pts, reb, ast, stl, blk, three_pm, fgm, fga, ftm, fta, turnovers, team_wins.",
        "import.no_source": "No projections found. Import a CSV file above.",
        "import.source": "Projection source",
        "import.demo_active": "DEMO DATA is displayed — not real NBA player projections.",
        "filter.search": "Search players",
        "filter.placeholder": "Enter a player name...",
        "filter.position": "Position",
        "filter.all": "All",
        "filter.sort": "Sort by",
        "filter.asc": "Ascending",
        "filter.total": "Players in view",
        "table.page_size": "Players per page",
        "table.page": "Table page",
        "table.player": "Player",
        "table.team": "Team",
        "table.positions": "Positions",
        "table.games": "Games",
        "table.note_per_game": "Stats: per-game averages. Missing projections remain blank (—). Z-score rankings still use season totals. Live Draft is below.",
        "table.note_season": "Stats: season totals. Missing projections remain blank (—). Z-score rankings still use season totals. Live Draft is below.",
        "stats.label": "Stats view",
        "stats.per_game": "Per game",
        "stats.season": "Season totals",
        "draft.empty_table": "No data to display.",
        "draft.new": "New draft session",
        "draft.session_name": "Session name",
        "draft.teams_input": "12 teams — one per line, in draft order",
        "draft.default_team": "Team {number}",
        "draft.create": "Create session",
        "draft.create_error": "Could not create session: {error}",
        "draft.created": "Draft session created.",
        "draft.edit_order": "Change team order — before the first pick only",
        "draft.edit_hint": "Reorder the lines to assign draft slots 1–12.",
        "draft.order": "Team order",
        "draft.save_order": "Save order",
        "draft.save_error": "Could not change team order: {error}",
        "draft.order_saved": "Team order saved.",
        "draft.search": "Search available players",
        "draft.position": "Available player position",
        "draft.available_count": "Available players in view",
        "draft.no_available": "No players match the current filters or source. Change filters or import more projections.",
        "draft.rank": "Rank",
        "draft.zscore": "Z-score (9 cat.)",
        "draft.categories_available": "Available categories",
        "draft.categories_missing": "Missing categories",
        "draft.show_50": "Showing the first 50 players. Refine your search to see more.",
        "draft.incomplete": "Some projections are incomplete — full Z-score rankings are unavailable.",
        "draft.player_select": "Player to draft",
        "draft.save_pick": "Save next pick",
        "draft.pick_error": "Could not save pick: {error}",
        "draft.pick_saved": "Pick #{number}: {player} saved in SQLite.",
        "draft.heading": "🏀 Live Draft — sessions, picks, and rankings",
        "draft.description": "Rankings use the full pool of projections from the selected source. Drafted players disappear from the available list below. TW is excluded from rankings.",
        "draft.no_sessions": "No draft sessions yet. Create one above.",
        "draft.session": "Draft session",
        "draft.progress": "**Progress:** {done}/{total} picks",
        "draft.on_clock": "On the clock: **{team}** · pick **#{number}** · round **{round}** · slot **{slot}**",
        "draft.finished": "Draft complete: all 156 picks have been recorded.",
        "draft.teams_heading": "Order of 12 teams",
        "draft.slot": "Slot",
        "draft.team": "Team",
        "draft.available": "Available players",
        "draft.available_error": "Could not load available players: {error}",
        "draft.picks": "Active pick history",
        "draft.number": "Number",
        "draft.round": "Round",
        "draft.player": "Player",
        "draft.no_picks": "No picks have been recorded yet.",
        "draft.undo_hint": "Only the latest pick can be undone.",
        "draft.undo_confirm": "Confirm undoing the latest pick",
        "draft.undo_button": "Undo last pick",
        "draft.undo_error": "Could not undo pick: {error}",
        "draft.undo_success": "Last pick undone.",
        "draft.events": "Event log — picks and undos",
        "draft.time": "Time",
        "draft.event": "Event",
        "draft.no_events": "Event log is empty.",
        "draft.limits": "The 90-second pick timer is not yet active. Demo data includes only 12 players; a complete 156-pick draft requires a larger CSV.",
        "draft.event.pick": "Pick",
        "draft.event.undo": "Undo",
        "draft.status.setup": "Setup",
        "draft.status.in_progress": "In progress",
        "draft.status.finished": "Finished",
    },
}

COLUMN_KEYS = {
    "Zawodnik": "table.player",
    "Zespół": "table.team",
    "Pozycje": "table.positions",
    "Mecze": "table.games",
}


def translate(key: str, language: str = DEFAULT_LANGUAGE, **values: object) -> str:
    """Translate a message, falling back to Polish for unknown languages."""
    locale = language if language in LANGUAGES else DEFAULT_LANGUAGE
    template = TEXT[locale][key]
    return template.format(**values)


def column_label(name: str, language: str | None = None) -> str:
    """Translate display-only column labels, keeping stat abbreviations stable."""
    return translate(COLUMN_KEYS[name], language or current_language()) if name in COLUMN_KEYS else name


def current_language() -> str:
    """Read the preferred language from this Streamlit browser session."""
    import streamlit as st

    selection = st.session_state.get("fantasy_language_preference", DEFAULT_LANGUAGE)
    return selection if selection in LANGUAGES else DEFAULT_LANGUAGE


def t(key: str, **values: object) -> str:
    """Translate a message using the current Streamlit session language."""
    return translate(key, current_language(), **values)


def language_selector() -> None:
    """Keep the chosen language across pages using a non-widget session key."""
    import streamlit as st

    saved = current_language()
    st.session_state["fantasy_language_preference"] = saved
    st.session_state["_fantasy_language_widget"] = saved

    def store_choice() -> None:
        st.session_state["fantasy_language_preference"] = st.session_state[
            "_fantasy_language_widget"
        ]

    st.sidebar.selectbox(
        "🌐 Language / Język",
        options=LANGUAGES,
        format_func=lambda language: "🇵🇱 Polski" if language == "pl" else "🇬🇧 English",
        key="_fantasy_language_widget",
        on_change=store_choice,
    )
