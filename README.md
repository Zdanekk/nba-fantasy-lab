
# NBA Fantasy Lab

A local Python application for NBA Fantasy Basketball
analytics, player projections, and draft management.

**Project status:** Phase 01 - Foundation & Draft Center

- **League:** Koszobidon Fantasy
- **Season:** 2026/27
- **Platform:** ESPN Fantasy Basketball


---

## Features

### Draft Center

- Import player projections from CSV files
- Persist player projections in SQLite
- Search players by name
- Filter players by eligible position
- Sort players by projected statistics
- Display per-game statistics by default
- Switch between per-game and season totals
- Display FG% and FT%
- Highlight missing projection data
- Support Polish and English interfaces

### Live Draft

- Create and manage draft sessions
- Configure the order of 12 fantasy teams
- Support 13 rounds of snake draft
- Generate up to 156 draft picks
- Record player selections in SQLite
- Prevent duplicate selections within a session
- Remove selected players from the available pool
- Undo the most recent selection
- Preserve a persistent draft event history
- Restore sessions after restarting Streamlit

### Player Rankings

- Calculate standard Z-scores
- Reverse the direction of turnovers (TO)
- Calculate volume-weighted FG% impact
- Calculate volume-weighted FT% impact
- Identify missing projections
- Exclude unverified Team Wins (TW) from rankings

---

## League Configuration

| Setting | Value |
|---------|-------|
| League | Koszobidon Fantasy |
| Platform | ESPN Fantasy Basketball |
| Season | 2026/27 |
| Scoring | Head to Head Each Category |
| Fantasy teams | 12 |
| Draft type | Snake |
| Draft rounds | 13 |
| Total draft picks | 156 |
| Pick timer | 90 seconds |
| Weekly acquisition limit | 7 |

### Scoring Categories

PTS, REB, AST, STL, BLK, 3PM, FG%, FT%, TO, TW

**Turnovers (TO):** Lower values are better.

**Team Wins (TW):** ESPN scoring rules must be verified
before implementing the final calculation.

### Roster Configuration

- PG: 1
- SG: 1
- SF: 1
- PF: 1
- C: 1
- G: 1
- F: 1
- UTIL: 3
- BE: 3
- IR: 1

Roster settings are stored in the league configuration.
Full roster eligibility and acquisition-limit enforcement
are outside the scope of Phase 01.

---

## Technology Stack

- Python 3.11+
- Streamlit
- SQLite (Python standard library)
- Pandas
- NumPy
- Plotly
- pytest
- Git and GitHub

The project does not require paid APIs, cloud hosting,
or a separate database server.

---

## Installation (Windows)

### 1. Prerequisites

Install:

- Python 3.11 or newer
- Git
- Visual Studio Code

### 2. Clone the repository

```powershell
git clone https://github.com/Zdanekk/nba-fantasy-lab.git
cd nba-fantasy-lab
```

### 3. Create a virtual environment

```powershell
py -3.11 -m venv .venv
```

### 4. Install dependencies

```powershell
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### 5. Initialize SQLite

```powershell
.\.venv\Scripts\python.exe -m nba_fantasy_lab.database
```

The SQLite database is created automatically at:

`data/nba_fantasy_lab.sqlite3`

### 6. Start the application

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Open:

http://localhost:8501

---

## Quick Start

1. Open the application in your browser.
2. Select Draft Center from the navigation menu.
3. Import a CSV file containing player projections.
4. Select the projection source.
5. Search, filter, and sort the player list.
6. Switch between per-game and season totals.
7. Create or open a Live Draft session.
8. Configure the draft team order before drafting.
9. Record picks and review draft history.
10. Undo the latest pick if necessary.

All draft records are stored locally in SQLite.

---

## CSV Data Format

Required columns:

- full_name
- nba_team
- positions

Multiple positions use a pipe separator:

`PG|SG`

Supported projection columns:

- games
- pts
- reb
- ast
- stl
- blk
- three_pm
- fgm
- fga
- ftm
- fta
- turnovers
- team_wins

Numerical projections represent season totals.

Per-game values are calculated by dividing season totals
by projected games.

FG% and FT% are calculated using makes and attempts.

Missing statistics remain missing; they are not
automatically replaced with zero.

### Demonstration Data

The repository includes:

`data/demo_projections.csv`

This file contains 12 fictional players and invented
statistics.

**Do not use demonstration data for real fantasy drafts.**

A full 12-team, 13-round draft requires at least
156 available players.

---

## Project Structure

```text
nba-fantasy-lab/
|-- app.py
|-- requirements.txt
|-- README.md
|-- .gitignore
|
|-- nba_fantasy_lab/
|   |-- __init__.py
|   |-- database.py
|   |-- importer.py
|   |-- ranking.py
|   |-- stat_views.py
|   |-- draft_engine.py
|   |-- draft_view.py
|   |-- draft_ui.py
|   `-- i18n.py
|
|-- pages/
|   `-- 1_Draft_Center.py
|
|-- data/
|   `-- demo_projections.csv
|
`-- tests/
    |-- test_database.py
    |-- test_importer.py
    |-- test_ranking.py
    |-- test_stat_views.py
    |-- test_draft_engine.py
    |-- test_draft_view.py
    `-- test_i18n.py
```

The local SQLite database and Python virtual environment
are intentionally excluded from version control.

---

## Automated Tests

Run the complete test suite:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Tests cover:

- SQLite schema initialization
- Database persistence
- Foreign key validation
- CSV validation and imports
- Duplicate import handling
- Missing projection values
- Snake draft scheduling
- Draft selections and undo operations
- Draft session persistence
- Z-score calculations
- Turnover direction
- Volume-weighted shooting percentages
- Per-game statistics
- Draft data views
- Polish and English translations

Phase 01 currently includes 40 passing tests,
verified in the development environment.

---

## Ranking Methodology

Standard Z-score:

`Z = (value - mean) / standard_deviation`

For turnovers, the direction is reversed.

Shooting percentages use volume-weighted impact
instead of raw shooting percentages alone.

FG impact:

`FGM - (pool_FG_percentage * FGA)`

FT impact:

`FTM - (pool_FT_percentage * FTA)`

These impacts are subsequently standardized.

The initial ranking uses nine verified scoring
categories. TW is excluded until the ESPN rules
are confirmed.

Incomplete projection data is explicitly indicated.

---

## Language Support

The application supports:

- Polish (PL)
- English (EN)

Language switching is handled through a shared
translation module.

The selected language is stored in the Streamlit
session. A completely new session may restore
the default language.

---

## Data Persistence and Security

SQLite stores local application data, including:

- Player information
- Player positions
- Projections
- League configuration
- Draft sessions
- Draft teams
- Draft picks
- Draft event history

The following must never be committed:

- Active SQLite databases
- Python virtual environments
- API keys or secrets
- Local environment files

The `.gitignore` file excludes these resources.

Back up the local SQLite database separately
before replacing your computer or deleting the project.

---

## Known Limitations

- ESPN Connector is not implemented.
- ESPN Team Wins rules remain unverified.
- Real player projections are not supplied.
- Demo data is fictional and incomplete for a full draft.
- The 90-second pick timer is stored in configuration
  but is not actively enforced.
- The weekly acquisition limit is not actively enforced.
- Automatic ESPN synchronization is not implemented.
- Full roster eligibility enforcement is not implemented.
- Rankings are projection-based, not weekly
  matchup simulations.
- Only the most recent active draft pick can be undone.
- Windows application-control policies may block
  PyArrow DLL loading.
- Draft Center uses an HTML table as a compatible
  display workaround.
- Cloud hosting and multi-user synchronization
  are outside the scope of Phase 01.

---

## Future Development

Potential Phase 02 improvements include:

- ESPN Connector
- ESPN league settings synchronization
- Stable ESPN player identifiers
- Real NBA player projections
- Expanded player pool
- Improved roster analysis
- Weekly matchup projections
- Additional category analytics
- Draft recommendations
- Automated data updates

Future features will be prioritized separately.

---

## License

No license has been selected yet.

The repository is intended for personal project
development unless a license is added.
