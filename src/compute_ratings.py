"""Computes Glicko-2 ratings and the ML match-prediction input table for
both tours. Replaces feature_engineering.ipynb.

Reads match_stats from Postgres (falls back to the CSV if DATABASE_URL isn't
set), writes ratings + ML input to Postgres and to data/prep/ as CSV.
"""

from db import get_engine, write_table, read_table
from glicko import GlickoRatingEngine, build_match_features, build_ml_input_table

TOURS = ["ATP", "WTA"]


def load_match_stats(engine):
    try:
        return read_table("match_stats", engine=engine)
    except Exception:
        import pandas as pd
        print("Falling back to CSV: could not read match_stats from Postgres")
        return pd.read_csv("../data/prep/match_stats.csv", low_memory=False)


def run_tour(engine, match_stats_df, tour):
    prefix = tour.lower()

    print(f"[{tour}] computing Glicko ratings...")
    ratings = GlickoRatingEngine().fit(match_stats_df, tour=tour)
    ratings.to_csv(f"../data/prep/{prefix}_glicko_output_df.csv", index=False)
    write_table(engine, ratings, f"{prefix}_glicko_ratings",
                index_cols=["player_name", "category", "date"])

    print(f"[{tour}] building match feature table...")
    features = build_match_features(match_stats_df, ratings, tour=tour)

    print(f"[{tour}] building ML input table...")
    ml_input = build_ml_input_table(features)
    ml_input.to_csv(f"../data/prep/{prefix}_ml_input.csv", index=False)
    write_table(engine, ml_input, f"{prefix}_ml_input",
                index_cols=["player_name", "match_date"])

    print(f"[{tour}] done: {len(ratings)} rating rows, {len(ml_input)} ML input rows")


if __name__ == "__main__":
    engine = get_engine()
    match_stats_df = load_match_stats(engine)
    for tour in TOURS:
        run_tour(engine, match_stats_df, tour)
