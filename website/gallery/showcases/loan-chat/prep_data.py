"""Build data/loans.parquet from OpenIntro's Lending Club extract.

Run once (`uv run python prep_data.py`) to regenerate the committed parquet.
Downloads the ~2.5 MB source CSV to data/.cache/ on first run.
"""

from pathlib import Path
from urllib.request import urlretrieve

import pandas as pd

SOURCE_URL = "https://www.openintro.org/data/csv/loans_full_schema.csv"
HERE = Path(__file__).parent
CACHE_CSV = HERE / "data" / ".cache" / "loans_full_schema.csv"
OUT_PARQUET = HERE / "data" / "loans.parquet"

KEEP_COLUMNS = [
    "state",
    "homeownership",
    "annual_income",
    "verified_income",
    "debt_to_income",
    "emp_length",
    "loan_purpose",
    "loan_amount",
    "term",
    "interest_rate",
    "grade",
    "sub_grade",
    "installment",
    "loan_status",
    "issue_month",
]


def main() -> None:
    if not CACHE_CSV.exists():
        CACHE_CSV.parent.mkdir(parents=True, exist_ok=True)
        print(f"Downloading {SOURCE_URL} ...", flush=True)
        urlretrieve(SOURCE_URL, CACHE_CSV)

    raw = pd.read_csv(CACHE_CSV)
    loans = raw[KEEP_COLUMNS].copy()
    loans.insert(0, "loan_id", range(1, len(loans) + 1))
    loans["loan_purpose"] = loans["loan_purpose"].str.replace("_", " ").str.title()

    OUT_PARQUET.parent.mkdir(parents=True, exist_ok=True)
    loans.to_parquet(OUT_PARQUET, index=False)
    print(f"Wrote {OUT_PARQUET} ({len(loans):,} rows, {len(loans.columns)} columns)")


if __name__ == "__main__":
    main()
