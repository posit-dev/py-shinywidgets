import json
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
    # CHR 2025 reports Connecticut only as the nine planning regions that
    # replaced its counties in 2022; the eight retired counties (09001-09015)
    # are entirely empty, so keeping both would double-count Connecticut and
    # leave the retired counties as pure imputation.
    df = df[~(df["fips"].str.startswith("09") & (df["fips"] < "09110"))]
    df, imputed = impute(df)
    tmp = OUT.with_suffix(".tmp")
    df.reset_index(drop=True).to_parquet(tmp, index=False)
    tmp.rename(OUT)
    RAW_CSV.unlink(missing_ok=True)
    print(f"{len(df):,} counties -> {OUT}")
    for feature, n in imputed.items():
        print(f"  imputed {n:,} missing values for {FEATURES[feature]!r}")
    write_supplement_geojson()


# Every FIPS the CHR data reports that plotly's (2013-vintage) counties file
# has no polygon for: Connecticut's nine planning regions (which replaced its
# counties in 2022), three newer Alaska county-equivalents, and Oglala Lakota
# County (renamed from Shannon County, with a new FIPS, in 2015).
SUPPLEMENT_GEOJSON_URL = (
    "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/"
    "State_County/MapServer/1/query?where=GEOID%20IN%20(%2702063%27%2C%2702066%27%2C%2702158%27%2C%2746102%27)"
    "%20OR%20STATE%3D%2709%27&outFields=GEOID&outSR=4326&f=geojson"
)
SUPPLEMENT_GEOJSON = DATA / "geojson-tiger-supplement.json"


def write_supplement_geojson() -> None:
    """Current-vintage Census TIGER boundaries for FIPS plotly's file lacks.

    The Census endpoint doesn't send CORS headers (so the app can't fetch it
    at runtime in the browser) -- commit a normalized copy instead: an `id`
    per feature to match the plotly file, and 5-decimal coordinates (~1 m),
    which shrinks the download by roughly half.
    """
    if SUPPLEMENT_GEOJSON.exists():
        return
    request = urllib.request.Request(
        SUPPLEMENT_GEOJSON_URL, headers={"User-Agent": "Mozilla/5.0"}
    )
    with urllib.request.urlopen(request) as resp:
        gj = json.load(resp)
    for feature in gj["features"]:
        feature["id"] = feature["properties"]["GEOID"]
        feature["properties"] = {"GEOID": feature["id"]}
        feature["geometry"]["coordinates"] = round_coords(
            feature["geometry"]["coordinates"]
        )
    tmp = SUPPLEMENT_GEOJSON.with_suffix(".tmp")
    with open(tmp, "w") as f:
        json.dump(gj, f, separators=(",", ":"))
    tmp.rename(SUPPLEMENT_GEOJSON)
    print(f"{len(gj['features'])} supplemental county shapes -> {SUPPLEMENT_GEOJSON}")


def round_coords(coords: object, digits: int = 5) -> object:
    if isinstance(coords, (int, float)):
        return round(coords, digits)
    return [round_coords(c, digits) for c in coords]  # type: ignore[union-attr]


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
