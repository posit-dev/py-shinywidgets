import shutil
import urllib.request
from pathlib import Path

import pandas as pd
from segments import FEATURES

CHR_URL = "https://www.countyhealthrankings.org/sites/default/files/media/document/analytic_data2025.csv"
DATA = Path(__file__).parent / "data"
RAW_CSV = DATA / "analytic_data2025.csv"
OUT = DATA / "counties.parquet"

# County Health Rankings columns -> our short feature names. All "raw value" columns,
# none derived from race/ethnicity breakdowns.
SOURCE_COLUMNS: dict[str, str] = {
    "5-digit FIPS Code": "fips",
    "State Abbreviation": "state",
    "Name": "county",
    "Population raw value": "population",
    "Median Household Income raw value": "median_income",
    "% Rural raw value": "pct_rural",
    "% 65 and Older raw value": "pct_65_older",
    "Some College raw value": "some_college",
    "Broadband Access raw value": "broadband",
    "Uninsured raw value": "uninsured",
    "Life Expectancy raw value": "life_expectancy",
    "Adult Obesity raw value": "adult_obesity",
}


def main() -> None:
    DATA.mkdir(exist_ok=True)
    download(CHR_URL, RAW_CSV)
    raw = pd.read_csv(
        RAW_CSV, skiprows=[1], dtype={"5-digit FIPS Code": str}, low_memory=False
    )
    counties = raw[raw["County FIPS Code"] != 0].copy()
    df = counties.loc[:, list(SOURCE_COLUMNS)].rename(columns=SOURCE_COLUMNS)
    df, imputed = impute(df)
    tmp = OUT.with_suffix(".tmp")
    df.reset_index(drop=True).to_parquet(tmp, index=False)
    tmp.rename(OUT)
    RAW_CSV.unlink(missing_ok=True)
    print(f"{len(df):,} counties -> {OUT}")
    for feature, n in imputed.items():
        print(f"  imputed {n:,} missing values for {FEATURES[feature]!r}")


def impute(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, int]]:
    df = df.copy()
    imputed: dict[str, int] = {}
    for feature in FEATURES:
        df[feature] = pd.to_numeric(df.loc[:, feature], errors="coerce")
        missing = df.loc[:, feature].isna()
        imputed[feature] = int(missing.sum())
        if not bool(missing.any()):
            continue
        state_median = df.groupby("state")[feature].transform("median")
        df[feature] = df.loc[:, feature].fillna(state_median)
        df[feature] = df.loc[:, feature].fillna(df.loc[:, feature].median())
    return df, imputed


def download(url: str, dest: Path) -> None:
    if dest.exists():
        return
    print(f"Downloading {dest.name} (~13 MB, one time) ...", flush=True)
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    part = dest.with_suffix(".part")
    with urllib.request.urlopen(request) as resp, open(part, "wb") as f:
        shutil.copyfileobj(resp, f, length=1 << 20)
    part.rename(dest)


if __name__ == "__main__":
    main()
