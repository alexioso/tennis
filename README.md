# Fantasy Tennis

A personal project that pulls ATP/WTA match data, builds player rating/performance
stats (including Glicko-2 ratings), and surfaces them through a couple of
front ends (a Streamlit dashboard and a static Firebase web app) for a
friends-league fantasy tennis game.

**Repo:** https://github.com/alexioso/tennis

This document reflects the state of the project as of 2026-07 — it's written to
re-orient after ~a year away, and to call out what needs to change to make this
a proper production pipeline rather than a folder of scripts + notebooks.

---

## 1. Data sources

Two sources feed the same match-level schema:

| Source | Coverage | Access | Where it lands |
|---|---|---|---|
| **SportRadar Tennis API** (trial tier) | Live/recent matches, ~2025-01-01 onward (older dates blocked by trial limits) | REST, API key in `src/.env` as `SPORTRADAR_API_KEY` | Raw daily JSON cached in `data/raw/daily_summary/{YYYYMMDD}.json`; season metadata cached in `data/raw/seasons/{season_id}.json` |
| **Jeff Sackmann's `tennis_atp` match archives** | Historical backfill, 2019–2024 | Static CSVs, manually downloaded | `data/raw/sackmann_atp_matches_{2019..2024}.csv` |

The SportRadar trial key expires/needs periodic renewal. `REFRESH_SPORTRADAR_API_KEY.md`
is a hand-written runbook for getting a new trial key from the SportRadar
marketplace and emailing it back to `alexbraksator@gmail.com` — this is a
manual, non-automated step today.

## 2. How the data is combined

**`src/data_pull.py`** is the core pipeline, run as a script (`python data_pull.py <days_back>`):

1. `get_tennis_daily_summary_range()` — hits the SportRadar `schedules/{date}/summaries.json`
   endpoint once per day in range (paginating past its 200-record page limit),
   writing raw JSON to `data/raw/daily_summary/`. Cached files are skipped on
   later runs, so only the trailing `<days_back>` window is re-fetched from the
   API each time (`refresh_to_git.sh` calls this with `120`).
2. `refresh_match_stats_df()` — reads the cached/fresh JSON per day, filters to
   singles matches with a completed status, and unpacks two rows per match
   (one per player) with serve/return/game/set stats. It then:
   - `pd.concat`s this with the pre-built Sackmann backfill table
     (`data/prep/retro/atp_sackmann.csv` — see below) to get one continuous
     match-level history back to 2019.
   - Computes derived rate stats (first/second serve win %, break point
     conversion %, ace %, etc.).
   - Joins surface/season info from `data/prep/seasons.csv`, calling the
     SportRadar `seasons/{id}/info.json` endpoint for any season not yet
     cached, and normalizes surface strings (hard/clay/grass/carpet, indoor flag).
   - Runs a handful of sanity-check rules that null out impossible values
     (e.g. win% > 100, points won > points played).
   - Writes the result to **`data/prep/match_stats.csv`** — the master
     match-level table (166k+ rows, 2019-01-01 → present).
3. `compute_player_summaries()` — aggregates `match_stats.csv` into per-player,
   per-year and per-month tables, split into ATP and WTA (United Cup counted
   in both), with rank columns (ace rank, DF rank, win rank, etc.) computed
   within each group. Writes:
   - `data/prep/atp_player_yearly_summary.csv` / `atp_player_monthly_summary.csv`
   - `data/prep/wta_player_yearly_summary.csv` / `wta_player_monthly_summary.csv`
4. `refresh_fantasy_data(fantasy_month)` — slices the monthly summary down to
   a fixed column set for the current fantasy scoring month and writes
   `data/fantasy/atp_player_summary.csv` / `wta_player_summary.csv`. **The
   target month is hardcoded in `data_pull.py`'s `__main__` block** and has to
   be bumped by hand each month — this is the main manual step in an otherwise
   scriptable pipeline.

**Sackmann backfill (`src/data_pull_sackmann.ipynb`)** — a one-time (per Sackmann
data update) notebook, not part of the daily run:
- Concatenates the yearly Sackmann CSVs, derives `event_id`/`match_date` from
  tournament + match number, and parses the free-text set score string
  (`parse_score()`) into per-set games/win-flags/tiebreak counts.
- Reshapes Sackmann's one-row-per-match/winner-loser format into the same
  one-row-per-player-per-match shape used by the SportRadar path.
- Reconciles player name formats between the two sources (SportRadar uses
  `"Last, First"`; Sackmann uses `"First Last"`) via a hand-maintained
  `name_fix` dictionary for ~100 known mismatches, then `rapidfuzz`
  fuzzy-matching against the existing `match_stats.csv` player list for
  anything else.
- Output: `data/prep/retro/atp_sackmann.csv`, consumed by `refresh_match_stats_df()` above.

## 3. Feature engineering & rating model

**`src/feature_engineering.ipynb`** — also run separately/manually, not wired
into `data_pull.py`:

- Computes **Glicko-2 ratings** (`glicko2` package) per player across 8
  category/surface combinations (`match_wins` and `set_wins`, each ×
  overall/hard/clay/grass), replaying `match_stats.csv` in chronological
  order and updating each player's rating after every match.
- Also precomputes empirical CDFs (`scipy.stats.ecdf`) for several rate
  stats (ace %, double-fault %, service-game-hold %, etc.), intended as
  percentile-normalized inputs to an ML model.
- Output: `data/prep/atp_glicko_output_df.csv` (558k rows — one row per
  player per match per rating category), which feeds the Streamlit dashboard.
- **Unfinished**: cell 0's TODOs and the cut-off `ml_pre_input` reshaping in
  cell 13 make clear the intent was a full match-outcome prediction model
  (features = both players' current Glicko + rate-stat percentiles,
  target = randomized win/loss flag to avoid winner/loser order leakage) —
  this was never completed.

## 4. AI agents

**There are no LLM/AI agents in this project currently.** The "intelligence"
today is entirely classical: Glicko-2 rating updates and groupby aggregations,
no language models or autonomous agents in the loop anywhere in
`data_pull.py`, the notebooks, or the apps.

The only references to this idea are TODO comments in `data_pull.py`
("fetch rally data from Sackmann... maybe train LLM?") — i.e. an unexplored
future idea, not built. If this direction is revisited, plausible entry
points would be a natural-language query layer over `match_stats.csv` /
the Glicko tables, or an agent that drafts fantasy-team recommendations from
the player summary tables — but none of this exists yet.

## 5. Where data lives & who reads/writes it

```
data/raw/            <- API/CSV inputs, effectively immutable once fetched
  daily_summary/*.json      written by  get_tennis_daily_summary()
  seasons/*.json             written by  get_season_info()
  sackmann_atp_matches_*.csv  manually downloaded, read by data_pull_sackmann.ipynb
  seasons.json               manually downloaded (SportRadar season list), read by data_pull_sackmann.ipynb

data/prep/            <- pipeline intermediate/derived tables
  retro/atp_sackmann.csv           written by data_pull_sackmann.ipynb  (one-time backfill)
  match_stats.csv                  written by refresh_match_stats_df()  (master table)
  seasons.csv                      written/appended by refresh_match_stats_df()
  {atp,wta}_player_{yearly,monthly}_summary.csv   written by compute_player_summaries()
  atp_glicko_output_df.csv         written by feature_engineering.ipynb

data/fantasy/          <- final, git-committed outputs
  {atp,wta}_player_summary.csv     written by refresh_fantasy_data(), consumed by the (unwired) web app
```

Only `data/fantasy/*.csv` is actually committed back to git today
(`src/refresh_to_git.sh` only `git add`s those two files). Everything under
`data/raw/` and `data/prep/` is regenerated/cached locally and currently
untracked, so `match_stats.csv` and the Glicko output only exist on whichever
machine last ran the pipeline — there's no shared/durable store for them yet.

## 6. Apps currently under development

**`src/dashboard_st.py`** — local-only Streamlit app (`streamlit run dashboard_st.py`).
Reads `data/prep/atp_glicko_output_df.csv` straight off disk, lets you pick a
Glicko category, surface, and player(s), and plots Glicko-2 trend lines with
95% CI bands plus a top-ranked-players table. This is the closer-to-working
of the two apps, but it's a dev/analysis tool, not the league-facing product.

**`app/`** — a static HTML/JS site meant to be the actual player-facing product
("Fantasy Tennis League"), currently early/scaffolded:
- `index.html` — login/signup page using **Firebase Authentication**
  (email/password + email verification + password reset), via the Firebase
  Web SDK loaded from `js/firebase.js` (project `fantasy-tennis-58cad`). This
  part is functional.
- `home.html` — embeds a public Google Sheets `pubhtml` view for "This
  Month's Results" — i.e. a manual spreadsheet, not wired to the CSV
  pipeline at all.
- `player-dashboard.html`, `team-scores.html`, `free-agents.html`,
  `raw-data.html` — scaffold pages that all pull from `js/data.js`, which is
  currently a **hardcoded stub object** (`window.leagueData` with a few
  dummy players/teams) rather than reading the real
  `data/fantasy/*.csv` outputs. None of these pages are connected to real
  data yet.
- `js/auth.js` — an older localStorage-based fake-login script that isn't
  referenced by any current HTML page; looks like a leftover from before
  Firebase Auth was wired in and is safe to delete.
- The top-level `/index.html` ("Hello, Localhost") is an unrelated scaffold/test
  page, not part of the app.

## 7. Running it locally

```bash
cd src
pip install -r requirements.txt     # pandas, numpy, requests, tqdm, python-dotenv,
                                     # rapidfuzz, scipy, glicko2, streamlit, plotly

# .env must define SPORTRADAR_API_KEY (see REFRESH_SPORTRADAR_API_KEY.md
# for how to obtain a trial key)

python data_pull.py <days_back>     # refresh last <days_back> days from the API,
                                     # rebuild match_stats.csv + summaries + fantasy CSVs
streamlit run dashboard_st.py       # local Glicko trend dashboard
```

`requirements.txt` is pinned to the versions currently running this pipeline
(Python 3.10, the `py310` conda env) rather than latest-of-everything. It
doesn't cover the two notebooks (`data_pull_sackmann.ipynb`,
`feature_engineering.ipynb`) — running those still needs a Jupyter frontend
of your choice pointed at the same environment.

`src/refresh_to_git.sh` is the current end-to-end "release" process: run
`data_pull.py 120`, then commit + push just the two `data/fantasy/*.csv`
files. Every commit in the repo's history titled "refresh data" comes from
running this by hand.

## 8. Known gaps / path to production

Things worth fixing as this moves from personal script collection to a
maintained pipeline:

- **No scheduling** — the whole pipeline is triggered by manually running
  `refresh_to_git.sh`. A cron job / GitHub Action / cloud scheduler calling
  `data_pull.py` would remove the manual step.
- **Hardcoded fantasy month** — `fantasy_month` in `data_pull.py`'s
  `__main__` has to be edited by hand every month; should derive from
  `date.today()`.
- **Secrets hygiene** — `src/.env` and `src/api_key.txt` hold the API key but
  aren't excluded by `.gitignore` (which currently only ignores `*.json`);
  they're untracked today by luck, not by rule. Worth adding both to
  `.gitignore` explicitly.
- **CSV-as-database** — `data_pull.py`'s own TODOs flag converting the
  CSV read/write pipeline to a real database; at 166k+ rows and growing,
  `match_stats.csv` is already a full-file rewrite on every run.
- **Notebooks in the critical path** — `data_pull_sackmann.ipynb` (Sackmann
  backfill) and `feature_engineering.ipynb` (Glicko/rating computation) are
  run manually and aren't part of `data_pull.py` or `refresh_to_git.sh` —
  the Glicko output (`atp_glicko_output_df.csv`) that the Streamlit dashboard
  depends on is only as fresh as the last manual notebook run.
  `feature_engineering.ipynb` also ends mid-implementation (an incomplete
  ML training table).
- **Web app not wired to real data** — `app/js/data.js` is a hardcoded
  stub; the four scaffold pages need to actually load
  `data/fantasy/{atp,wta}_player_summary.csv` (or a small API in front of
  them) instead of dummy data.
- **Only `data/fantasy/*.csv` is version-controlled** — the master
  `match_stats.csv` and rating tables live only on a local machine; consider
  at minimum a shared bucket/DB, since regenerating history depends on the
  SportRadar trial key covering old dates, which it currently doesn't.
- **Dead code** — `app/js/auth.js` (superseded by Firebase auth), the
  top-level `/index.html` scaffold, and the empty `app/lsof` file appear to
  be leftovers safe to remove.
