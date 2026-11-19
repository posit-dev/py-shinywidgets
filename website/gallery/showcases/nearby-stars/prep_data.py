import io
import time
import urllib.parse
import urllib.request
from pathlib import Path

import pandas as pd

from stars import fast_mask, hyades_mask, prep_stars, white_dwarf_mask

TAP_URL = "https://gea.esac.esa.int/tap-server/tap/sync"
DATA = Path(__file__).parent / "data"


def main() -> None:
    DATA.mkdir(exist_ok=True)
    out = DATA / "stars.parquet"
    n = prep_stars(out, fetch_tap)
    df = pd.read_parquet(out)
    print(f"{n:,} stars -> {out}")
    print(f"hyades: {int(hyades_mask(df).sum()):,}")
    print(f"fast movers: {int(fast_mask(df).sum()):,}")
    print(f"white dwarfs: {int(white_dwarf_mask(df).sum()):,}")


def fetch_tap(query: str, retries: int = 3) -> pd.DataFrame:
    body = urllib.parse.urlencode(
        {"REQUEST": "doQuery", "LANG": "ADQL", "FORMAT": "csv", "QUERY": query}
    ).encode()
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(TAP_URL, data=body, timeout=300) as resp:
                df = pd.read_csv(io.BytesIO(resp.read()))
            print(f"  {len(df):>6,} rows  {query.split('AND ra')[-1].strip()}", flush=True)
            return df
        except OSError:
            if attempt == retries - 1:
                raise
            time.sleep(5 * (attempt + 1))
    raise AssertionError("unreachable")


if __name__ == "__main__":
    main()
