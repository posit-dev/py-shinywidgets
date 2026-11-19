from collections.abc import Callable
from pathlib import Path

import numpy as np
import pandas as pd
from astropy.table import Table

GAIA_QUERY = (
    "SELECT source_id, ra, dec, l, b, parallax, pmra, pmdec, radial_velocity, "
    "phot_g_mean_mag, bp_rp, ruwe FROM gaiadr3.gaia_source "
    "WHERE parallax > 10 AND parallax_over_error > 10 AND bp_rp IS NOT NULL"
)
TAP_ROW_CAP = 50_000
MAX_SKY_MARKERS = 3_000


def add_derived(df: pd.DataFrame) -> pd.DataFrame:
    dist = 1000 / df["parallax"]
    l_rad = np.radians(df["l"])
    b_rad = np.radians(df["b"])
    return df.assign(
        dist_pc=dist,
        abs_g=df["phot_g_mean_mag"] + 5 * np.log10(df["parallax"] / 100),
        vtan=4.74047 * np.hypot(df["pmra"], df["pmdec"]) / df["parallax"],
        x=dist * np.cos(b_rad) * np.cos(l_rad),
        y=dist * np.cos(b_rad) * np.sin(l_rad),
        z=dist * np.sin(b_rad),
    )


def hyades_mask(df: pd.DataFrame) -> pd.Series:
    return (
        df["ra"].between(50, 85)
        & df["dec"].between(0, 30)
        & df["pmra"].between(70, 140)
        & df["pmdec"].between(-50, -5)
        & df["dist_pc"].between(35, 60)
    )


def fast_mask(df: pd.DataFrame, vtan_min: float = 150.0) -> pd.Series:
    return df["vtan"] > vtan_min


def white_dwarf_mask(df: pd.DataFrame) -> pd.Series:
    return (df["abs_g"] > 3.33 * df["bp_rp"] + 9.5) & (df["bp_rp"] < 1.5)


def sky_table(df: pd.DataFrame, n: int = MAX_SKY_MARKERS) -> Table:
    brightest = df.nsmallest(n, "phot_g_mean_mag")[["ra", "dec", "source_id", "dist_pc"]]
    return Table.from_pandas(brightest.reset_index(drop=True))


def adql_slices(step: int = 20) -> list[str]:
    return [adql_query(lo, lo + step) for lo in range(0, 360, step)]


def adql_query(lo: float, hi: float) -> str:
    return f"{GAIA_QUERY} AND ra >= {lo:g} AND ra < {hi:g}"


def prep_stars(
    out_path: Path,
    fetch: Callable[[str], pd.DataFrame],
    step: int = 20,
) -> int:
    if not out_path.exists():
        frames = [fetch_range(fetch, lo, lo + step) for lo in range(0, 360, step)]
        df = pd.concat(frames, ignore_index=True)
        df = add_derived(df[df["ruwe"] < 1.4].reset_index(drop=True))
        tmp = out_path.with_suffix(".tmp")
        df.to_parquet(tmp, index=False)
        tmp.rename(out_path)
    return len(pd.read_parquet(out_path, columns=["source_id"]))


def fetch_range(fetch: Callable[[str], pd.DataFrame], lo: float, hi: float) -> pd.DataFrame:
    df = fetch(adql_query(lo, hi))
    if len(df) < TAP_ROW_CAP:
        return df
    mid = (lo + hi) / 2
    return pd.concat([fetch_range(fetch, lo, mid), fetch_range(fetch, mid, hi)], ignore_index=True)
