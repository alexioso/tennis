import os
import re

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")


def get_engine():
    if not DATABASE_URL:
        raise RuntimeError(
            "DATABASE_URL not set. Add it to src/.env, e.g.\n"
            "DATABASE_URL=postgresql://user:password@host:5432/dbname?sslmode=require"
        )
    return create_engine(DATABASE_URL)


def _to_snake_case(col):
    col = str(col).strip().replace("%", "pct")
    col = re.sub(r"[^0-9a-zA-Z]+", "_", col)
    col = re.sub(r"_+", "_", col).strip("_").lower()
    return col or "col"


def _clean_for_db(df):
    # drop pandas index artifacts left over from repeated to_csv()/read_csv() round trips
    df = df.loc[:, ~df.columns.str.match(r"(?i)^unnamed", na=False)]
    df = df.drop(columns=["index"], errors="ignore")
    return df.rename(columns={c: _to_snake_case(c) for c in df.columns})


def write_table(engine, df, table_name, index_cols=None):
    """Fully replace `table_name` with the contents of `df`.

    Mirrors the full-file-overwrite semantics of the existing to_csv() calls:
    each refresh rebuilds the table from scratch rather than upserting.
    """
    df = _clean_for_db(df)
    # postgres caps bind parameters per statement at 65535; method="multi" packs
    # chunksize * num_columns of them into one INSERT, so wide tables need smaller chunks
    chunksize = max(1, 60000 // max(len(df.columns), 1))
    with engine.begin() as conn:
        df.to_sql(
            table_name,
            conn,
            if_exists="replace",
            index=False,
            method="multi",
            chunksize=chunksize,
        )
        for col in index_cols or []:
            conn.execute(
                text(
                    f'CREATE INDEX IF NOT EXISTS idx_{table_name}_{col} '
                    f'ON "{table_name}" ("{col}")'
                )
            )


def read_sql(sql, params=None, engine=None):
    """Run a SELECT statement and return the result as a DataFrame.

    Use SQLAlchemy-style named params (:name) rather than f-string/format
    interpolation, so values are bound safely instead of pasted into the
    query text. Example:

        read_sql("SELECT * FROM match_stats WHERE player_name = :name",
                 {"name": "Alcaraz, Carlos"})
    """
    engine = engine or get_engine()
    return pd.read_sql(text(sql), engine, params=params)


def read_table(table_name, engine=None):
    """Convenience wrapper: SELECT * FROM table_name."""
    engine = engine or get_engine()
    return pd.read_sql(f'SELECT * FROM "{table_name}"', engine)
