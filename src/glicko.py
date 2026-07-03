"""Glicko-2 player rating engine, replacing feature_engineering.ipynb.

Replays a tour's match history chronologically and maintains Glicko-2 ratings
across several stat families (match wins, set wins, tiebreaks, service holds
vs return breaks, second-serve win vs second-serve return), each tracked both
"overall" and per surface.
"""

import math

import numpy as np
import pandas as pd
from scipy import stats
from tqdm import tqdm

# ---- vendored Glicko-2 core (github.com/sublee/glicko2) ----

WIN = 1.
DRAW = 0.5
LOSS = 0.


class Rating:
    def __init__(self, mu, phi, sigma):
        self.mu = mu
        self.phi = phi
        self.sigma = sigma

    def __repr__(self):
        return f"Rating(mu={self.mu:.3f}, phi={self.phi:.3f}, sigma={self.sigma:.3f})"


class Glicko2:
    def __init__(self, mu, phi, sigma, tau, epsilon):
        self.mu = mu
        self.phi = phi
        self.sigma = sigma
        self.tau = tau
        self.epsilon = epsilon

    def create_rating(self, mu=None, phi=None, sigma=None):
        return Rating(mu if mu is not None else self.mu,
                       phi if phi is not None else self.phi,
                       sigma if sigma is not None else self.sigma)

    def scale_down(self, rating, ratio=173.7178):
        return self.create_rating((rating.mu - self.mu) / ratio, rating.phi / ratio, rating.sigma)

    def scale_up(self, rating, ratio=173.7178):
        return self.create_rating(rating.mu * ratio + self.mu, rating.phi * ratio, rating.sigma)

    def reduce_impact(self, rating):
        return 1. / math.sqrt(1 + (3 * rating.phi ** 2) / (math.pi ** 2))

    def expect_score(self, rating, other_rating, impact):
        return 1. / (1 + math.exp(-impact * (rating.mu - other_rating.mu)))

    def determine_sigma(self, rating, difference, variance):
        phi = rating.phi
        difference_squared = difference ** 2
        alpha = math.log(rating.sigma ** 2)

        def f(x):
            tmp = phi ** 2 + variance + math.exp(x)
            a = math.exp(x) * (difference_squared - tmp) / (2 * tmp ** 2)
            b = (x - alpha) / (self.tau ** 2)
            return a - b

        a = alpha
        if difference_squared > phi ** 2 + variance:
            b = math.log(difference_squared - phi ** 2 - variance)
        else:
            k = 1
            while f(alpha - k * math.sqrt(self.tau ** 2)) < 0:
                k += 1
            b = alpha - k * math.sqrt(self.tau ** 2)
        f_a, f_b = f(a), f(b)
        while abs(b - a) > self.epsilon:
            c = a + (a - b) * f_a / (f_b - f_a)
            f_c = f(c)
            if f_c * f_b < 0:
                a, f_a = b, f_b
            else:
                f_a /= 2
            b, f_b = c, f_c
        return math.exp(1) ** (a / 2)

    def rate(self, rating, series):
        rating = self.scale_down(rating)
        if not series:
            phi_star = math.sqrt(rating.phi ** 2 + rating.sigma ** 2)
            return self.scale_up(self.create_rating(rating.mu, phi_star, rating.sigma))
        variance_inv = 0
        difference = 0
        for actual_score, other_rating in series:
            other_rating = self.scale_down(other_rating)
            impact = self.reduce_impact(other_rating)
            expected_score = self.expect_score(rating, other_rating, impact)
            variance_inv += impact ** 2 * expected_score * (1 - expected_score)
            difference += impact * (actual_score - expected_score)
        difference /= variance_inv
        variance = 1. / variance_inv
        sigma = self.determine_sigma(rating, difference, variance)
        phi_star = math.sqrt(rating.phi ** 2 + sigma ** 2)
        phi = 1. / math.sqrt(1 / phi_star ** 2 + 1 / variance)
        mu = rating.mu + phi ** 2 * (difference / variance)
        return self.scale_up(self.create_rating(mu, phi, sigma))


# ---- rating engine ----

SURFACES = ["hard", "clay", "grass"]
BASE_STATS = ["match_wins", "tiebreak", "set_wins",
              "service_hold_wins", "return_break_wins",
              "second_serve_win", "second_serve_return_win"]

DEFAULT_GLICKO_PARAMS = dict(tau=0.5, mu=1500, phi=350, sigma=0.06, epsilon=1e-6)
# service_hold/return_break ratings move on every service game rather than
# every match, so they get a lower volatility ceiling than the rest
LOW_VOLATILITY_STATS = {"service_hold_wins", "return_break_wins"}

TOUR_CATEGORIES = {
    "ATP": ["ATP", "United Cup"],
    "WTA": ["WTA", "United Cup"],
}


def _valid_denominator(x):
    return not pd.isnull(x) and x != 0


class GlickoRatingEngine:
    """Replays match_stats chronologically, maintaining Glicko-2 ratings for
    BASE_STATS x {overall, hard, clay, grass}.

    One row of output is recorded per (player, category) per match, holding
    that player's rating *after* the match is applied.
    """

    def __init__(self, glicko_params=None):
        params = {**DEFAULT_GLICKO_PARAMS, **(glicko_params or {})}
        self.envs = {}
        for stat in BASE_STATS:
            sigma = 0.01 if stat in LOW_VOLATILITY_STATS else params["sigma"]
            for suffix in ["overall"] + SURFACES:
                category = f"{stat}_{suffix}"
                self.envs[category] = Glicko2(mu=params["mu"], phi=params["phi"],
                                               sigma=sigma, tau=params["tau"],
                                               epsilon=params["epsilon"])
        self.ratings = {}
        self._rows = []

    def _suffixes_for(self, surface):
        suffixes = ["overall"]
        if surface in SURFACES:
            suffixes.append(surface)
        return suffixes

    def _init_players(self, players):
        for category, env in self.envs.items():
            self.ratings[category] = {p: env.create_rating() for p in players}

    def _rate_pair(self, cat_a, cat_b, entity_a, entity_b, score_a, score_b):
        """Rate entity_a's performance (score_a) in cat_a against entity_b's
        PRIOR cat_b rating, and entity_b's performance (score_b) in cat_b
        against entity_a's PRIOR cat_a rating. Covers both same-category
        symmetric updates (cat_a == cat_b) and cross-category pairs."""
        prior_a = self.ratings[cat_a][entity_a]
        prior_b = self.ratings[cat_b][entity_b]
        self.ratings[cat_a][entity_a] = self.envs[cat_a].rate(prior_a, [(score_a, prior_b)])
        self.ratings[cat_b][entity_b] = self.envs[cat_b].rate(prior_b, [(score_b, prior_a)])

    def _record(self, category, player, event_id, date):
        rating = self.ratings[category][player]
        self._rows.append((category, date, event_id, player, rating.mu, rating.phi, rating.sigma))

    def _process_match_wins(self, player, opponent, event_id, date, winner_flag, surface):
        if winner_flag not in (0, 1):
            return
        for suffix in self._suffixes_for(surface):
            cat = f"match_wins_{suffix}"
            self._rate_pair(cat, cat, player, opponent, winner_flag, 1 - winner_flag)
            self._record(cat, player, event_id, date)
            self._record(cat, opponent, event_id, date)

    def _process_tiebreaks(self, player, opponent, event_id, date, player_tb_won, opp_tb_won, surface):
        if player_tb_won == 0 and opp_tb_won == 0:
            return
        for suffix in self._suffixes_for(surface):
            cat = f"tiebreak_{suffix}"
            for _ in range(player_tb_won):
                self._rate_pair(cat, cat, player, opponent, WIN, LOSS)
            for _ in range(opp_tb_won):
                self._rate_pair(cat, cat, player, opponent, LOSS, WIN)
            self._record(cat, player, event_id, date)
            self._record(cat, opponent, event_id, date)

    def _process_sets(self, player, opponent, event_id, date, set_win_flags, surface):
        played_any = any(not pd.isnull(f) for f in set_win_flags)
        if not played_any:
            return
        for suffix in self._suffixes_for(surface):
            cat = f"set_wins_{suffix}"
            for flag in set_win_flags:
                if pd.isnull(flag):
                    continue
                self._rate_pair(cat, cat, player, opponent, flag, 1 - flag)
            self._record(cat, player, event_id, date)
            self._record(cat, opponent, event_id, date)

    def _process_service_return(self, player, opponent, event_id, date,
                                 player_holds, player_games, opp_holds, opp_games, surface):
        if not _valid_denominator(player_games) or not _valid_denominator(opp_games):
            return
        player_hold_pct = player_holds / player_games
        opp_hold_pct = opp_holds / opp_games
        for suffix in self._suffixes_for(surface):
            shw, rbw = f"service_hold_wins_{suffix}", f"return_break_wins_{suffix}"
            self._rate_pair(shw, rbw, player, opponent, player_hold_pct, 1 - player_hold_pct)
            self._rate_pair(shw, rbw, opponent, player, opp_hold_pct, 1 - opp_hold_pct)
            self._record(shw, player, event_id, date)
            self._record(shw, opponent, event_id, date)
            self._record(rbw, player, event_id, date)
            self._record(rbw, opponent, event_id, date)

    def _process_second_serve(self, player, opponent, event_id, date,
                               player_2s_won, player_2s_total, opp_2s_won, opp_2s_total,
                               surface, win_cdf, return_cdf):
        if not _valid_denominator(player_2s_total) or not _valid_denominator(opp_2s_total):
            return
        player_win_pct = player_2s_won / player_2s_total
        opp_win_pct = opp_2s_won / opp_2s_total
        player_win_score = win_cdf.cdf.evaluate(player_win_pct)
        opp_win_score = win_cdf.cdf.evaluate(opp_win_pct)
        # returner's raw return-win% is just 1 - server's win% (same point, other side)
        player_return_score = return_cdf.cdf.evaluate(1 - opp_win_pct)
        opp_return_score = return_cdf.cdf.evaluate(1 - player_win_pct)
        for suffix in self._suffixes_for(surface):
            ssw, ssrw = f"second_serve_win_{suffix}", f"second_serve_return_win_{suffix}"
            self._rate_pair(ssw, ssrw, player, opponent, player_win_score, opp_return_score)
            self._rate_pair(ssw, ssrw, opponent, player, opp_win_score, player_return_score)
            self._record(ssw, player, event_id, date)
            self._record(ssw, opponent, event_id, date)
            self._record(ssrw, player, event_id, date)
            self._record(ssrw, opponent, event_id, date)

    def fit(self, match_stats_df, tour):
        """match_stats_df: the full match_stats table (one row per player per
        match). tour: 'ATP' or 'WTA'. Returns the long-format ratings history
        (one row per player per match per category)."""
        categories = TOUR_CATEGORIES[tour]
        df = match_stats_df[match_stats_df["competition_category"].isin(categories)].copy()
        df = df.sort_values(["match_date", "event_id"]).reset_index(drop=True)

        self._init_players(df["player_name"].unique())

        second_serve_win_cdf = stats.ecdf(
            df.loc[df["second_serve_win_perc"].notnull(), "second_serve_win_perc"] / 100)
        second_serve_return_win_cdf = stats.ecdf(
            df.loc[df["second_serve_return_win_perc"].notnull(), "second_serve_return_win_perc"] / 100)

        for i in tqdm(df.index[::2], desc=f"{tour} Glicko"):
            player_row = df.loc[i]
            opp_row = df.loc[i + 1]
            player, opponent = player_row["player_name"], opp_row["player_name"]
            event_id, date, surface = player_row["event_id"], player_row["match_date"], player_row["surface"]

            self._process_match_wins(player, opponent, event_id, date,
                                      player_row["winner_flag"], surface)

            player_tb_won = player_row["tiebreaks_won"]
            opp_tb_won = player_row["tiebreaks_lost"]
            self._process_tiebreaks(player, opponent, event_id, date,
                                     0 if pd.isnull(player_tb_won) else int(player_tb_won),
                                     0 if pd.isnull(opp_tb_won) else int(opp_tb_won), surface)

            set_flags = [player_row.get(f"set{n}_win_flag") for n in range(1, 6)]
            self._process_sets(player, opponent, event_id, date, set_flags, surface)

            self._process_service_return(player, opponent, event_id, date,
                                          player_row["service_games_held"], player_row["service_games"],
                                          opp_row["service_games_held"], opp_row["service_games"], surface)

            self._process_second_serve(player, opponent, event_id, date,
                                        player_row["second_serve_points_won"], player_row["second_serve_successful"],
                                        opp_row["second_serve_points_won"], opp_row["second_serve_successful"],
                                        surface, second_serve_win_cdf, second_serve_return_win_cdf)

        out = pd.DataFrame(self._rows, columns=[
            "category", "date", "event_id", "player_name", "glicko2_mu", "glicko2_phi", "glicko2_sigma"
        ])
        out = out.sort_values(["player_name", "category", "date"])
        out["glicko2_mu_lower"] = out["glicko2_mu"] - 1.96 * out["glicko2_phi"]
        out["glicko2_mu_upper"] = out["glicko2_mu"] + 1.96 * out["glicko2_phi"]
        out["surface"] = out["category"].str.rsplit("_", n=1).str[-1]
        out["glicko2_category"] = out["category"].str.replace("_overall", "").str.replace("_hard", "") \
            .str.replace("_clay", "").str.replace("_grass", "").str.replace("_", " ")
        return out


GLICKO_ML_PARAMS = ["glicko2_mu", "glicko2_mu_lower"]


def build_match_features(match_stats_df, ratings_df, tour):
    """Attach each player's own and their opponent's most recent PRE-match
    Glicko ratings (all categories, with the per-category surface variants
    condensed down to whichever surface each match was actually played on)
    onto match_stats. Returns one row per player per match.
    """
    categories = TOUR_CATEGORIES[tour]
    ms = match_stats_df[match_stats_df["competition_category"].isin(categories)].copy()
    ms = ms.sort_values(["match_date", "event_id"]).reset_index(drop=True)

    ratings = ratings_df.sort_values(["player_name", "category", "date"]).copy()
    # ratings_df stores the rating AS OF AFTER each match; shifting by one
    # within (player, category) turns that into the rating AS OF BEFORE the
    # player's next match, which is what a predictive feature must use
    ratings[GLICKO_ML_PARAMS] = ratings.groupby(["player_name", "category"])[GLICKO_ML_PARAMS].shift(1)

    base_categories = ratings["glicko2_category"].str.replace(" ", "_").unique()

    pivot = ratings.pivot(index=["player_name", "date", "event_id", "surface"],
                           columns="category", values=GLICKO_ML_PARAMS).reset_index()
    pivot.columns = ["_".join(map(str, c)) if c[1] != "" else c[0] for c in pivot.columns.values]
    pivot = pivot.rename(columns={"date": "match_date"})
    pivot = (pivot.drop(columns=["surface"])
                  .groupby(["player_name", "match_date", "event_id"]).max().reset_index()
                  .merge(ms[["player_name", "match_date", "event_id", "surface"]], how="left"))

    match_surfaces = [s for s in pivot["surface"].dropna().unique() if s in SURFACES]
    col_idx = pd.Series(range(len(match_surfaces)), index=match_surfaces)
    surface_idx = pivot["surface"].map(col_idx)
    known = surface_idx.notnull()
    for c in base_categories:
        for p in GLICKO_ML_PARAMS:
            score_cols = [f"{p}_{c}_{s}" for s in match_surfaces]
            if any(sc not in pivot.columns for sc in score_cols):
                continue
            picked = np.full(len(pivot), np.nan)
            scores = pivot.loc[known, score_cols].to_numpy()
            picked[known.to_numpy()] = scores[np.arange(known.sum()), surface_idx[known].astype(int).to_numpy()]
            pivot[f"{p}_{c}_surface"] = picked
            pivot = pivot.drop(columns=score_cols)

    pivot.columns = [f"player_{c}" if "glicko" in c else c for c in pivot.columns]
    out = ms.merge(pivot, how="left", on=["player_name", "match_date", "event_id"])
    pivot.columns = [c.replace("player_", "opponent_") for c in pivot.columns]
    out = out.merge(pivot, how="left", on=["opponent_name", "match_date", "event_id"])
    return out


def build_ml_input_table(match_features_df, random_state=42):
    """Collapse the per-player-per-match feature table into one row per
    match, randomly assigning which side is "player" vs "opponent" so a
    model can't shortcut on row order (most of the historical Sackmann
    backfill lists the winner first). Returns one row per match with
    player_glicko_*/opponent_glicko_* features and a `player_won` target.
    """
    rng = np.random.RandomState(random_state)
    df = match_features_df.reset_index(drop=True)
    player_glicko_cols = [c for c in df.columns if c.startswith("player_glicko")]

    context_cols = ["match_date", "event_id", "competition_name", "competition_category",
                     "competition_level", "surface", "player_seed", "opponent_seed"]
    context_cols = [c for c in context_cols if c in df.columns]

    flip = rng.random_sample(len(df) // 2) < 0.5
    rows = []
    for match_num, i in enumerate(range(0, len(df), 2)):
        a, b = df.loc[i], df.loc[i + 1]
        player_row, opp_row = (b, a) if flip[match_num] else (a, b)

        row = {c: player_row[c] for c in context_cols}
        row["player_name"] = player_row["player_name"]
        row["opponent_name"] = opp_row["player_name"]
        row["player_won"] = int(player_row["winner_flag"]) if player_row["winner_flag"] in (0, 1) else np.nan
        for c in player_glicko_cols:
            row[c] = player_row[c]
            row[c.replace("player_", "opponent_")] = opp_row[c]
        rows.append(row)

    return pd.DataFrame(rows)
