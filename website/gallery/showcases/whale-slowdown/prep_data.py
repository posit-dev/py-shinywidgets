import shutil
import urllib.request
import zipfile
from pathlib import Path

import duckdb

from ships import prep_pings

AIS_URL = "https://coast.noaa.gov/htdata/CMSP/AISDataHandler/2023/AIS_2023_06_01.zip"
DATA = Path(__file__).parent / "data"


def main() -> None:
    DATA.mkdir(exist_ok=True)
    out = DATA / "pings.parquet"
    zip_path = DATA / "AIS_2023_06_01.zip"
    csv_path = DATA / "AIS_2023_06_01.csv"
    if not out.exists():
        if not csv_path.exists():
            if not zip_path.exists():
                download(AIS_URL, zip_path)
            with zipfile.ZipFile(zip_path) as zf:
                member = next(m for m in zf.namelist() if m.endswith(".csv"))
                with zf.open(member) as src, open(csv_path.with_suffix(".part"), "wb") as dst:
                    shutil.copyfileobj(src, dst, length=1 << 20)
            csv_path.with_suffix(".part").rename(csv_path)

    con = duckdb.connect()
    n = prep_pings(con, csv_path, out)
    csv_path.unlink(missing_ok=True)
    vessels = con.execute("SELECT count(DISTINCT mmsi) FROM read_parquet(?)", [str(out)]).fetchone()
    print(f"{n:,} moving pings from {vessels[0] if vessels else 0:,} vessels -> {out}")


def download(url: str, dest: Path) -> None:
    part = dest.with_suffix(".part")
    with urllib.request.urlopen(url) as resp, open(part, "wb") as f:
        shutil.copyfileobj(resp, f, length=1 << 20)
    part.rename(dest)


if __name__ == "__main__":
    main()
