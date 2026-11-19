from pathlib import Path

import duckdb
import pandas as pd

VESSEL_GROUPS: dict[str, tuple[int, ...]] = {
    "cargo": tuple(range(70, 80)),
    "tanker": tuple(range(80, 90)),
    "passenger": tuple(range(60, 70)),
    "fishing": (30,),
    "tug": (31, 32, 52),
    "pleasure": (36, 37),
}

MAX_HIGHLIGHT = 300_000


def vessel_group_sql(col: str = "VesselType") -> str:
    whens = " ".join(
        f"WHEN {col} IN ({', '.join(map(str, codes))}) THEN '{group}'"
        for group, codes in VESSEL_GROUPS.items()
    )
    return f"CASE {whens} ELSE 'other' END"


def prep_pings(
    con: duckdb.DuckDBPyConnection,
    csv_path: Path,
    out_path: Path,
    min_sog: float = 0.5,
) -> int:
    if not out_path.exists():
        tmp = out_path.with_suffix(".tmp")
        tmp.unlink(missing_ok=True)
        vtype = vessel_group_sql("TRY_CAST(VesselType AS INTEGER)")
        con.execute(
            f"""
            COPY (
                SELECT
                    TRY_CAST(MMSI AS BIGINT) AS mmsi,
                    TRY_CAST(BaseDateTime AS TIMESTAMP) AS ts,
                    hour(TRY_CAST(BaseDateTime AS TIMESTAMP))::INT AS hour,
                    TRY_CAST(LON AS DOUBLE) AS lon,
                    TRY_CAST(LAT AS DOUBLE) AS lat,
                    TRY_CAST(SOG AS DOUBLE) AS sog,
                    {vtype} AS vessel_group,
                    NULLIF(trim(VesselName), '') AS name,
                    TRY_CAST(TRY_CAST(Length AS DOUBLE) AS INTEGER) AS length
                FROM read_csv(?, header = true, all_varchar = true)
                WHERE TRY_CAST(SOG AS DOUBLE) >= ? AND TRY_CAST(SOG AS DOUBLE) < 40
            ) TO '{tmp}' (FORMAT parquet)
            """,
            [str(csv_path), min_sog],
        )
        tmp.rename(out_path)
    row = con.execute("SELECT count(*) FROM read_parquet(?)", [str(out_path)]).fetchone()
    assert row is not None
    return int(row[0])


def slowpokes(
    rel: duckdb.DuckDBPyRelation,
    min_median_sog: float = 12.0,
    limit: int = 15,
) -> pd.DataFrame:
    return rel.query(
        "sel",
        f"""
        SELECT
            any_value(name) AS name,
            any_value(vessel_group) AS vessel_group,
            count(*) AS pings,
            median(sog) AS median_sog
        FROM sel
        GROUP BY mmsi
        HAVING count(*) >= 20 AND median(sog) >= {float(min_median_sog)}
        ORDER BY median_sog DESC
        LIMIT {int(limit)}
        """,
    ).df()


def highlight_sample(rel: duckdb.DuckDBPyRelation, n: int = MAX_HIGHLIGHT) -> pd.DataFrame:
    row = rel.query("sel", "SELECT count(*) FROM sel").fetchone()
    assert row is not None
    sample = f"USING SAMPLE {int(n)} ROWS" if row[0] > n else ""
    return rel.query("sel", f"SELECT lon, lat, sog FROM sel {sample}").df()
