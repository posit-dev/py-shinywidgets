import json
from pathlib import Path

import pandas as pd
from embedding_atlas.projection import compute_projection

from issues import clean_body, find_twins, language_of

DATA = Path(__file__).parent / "data"
COLUMNS = [
    "repo", "language", "number", "title", "text", "state", "year", "created_at", "closed_at",
    "comments", "reactions", "labels", "url", "projection_x", "projection_y", "neighbors", "twin",
]  # fmt: skip


def main() -> None:
    rows = [
        json.loads(line)
        for path in sorted((DATA / "raw").glob("*.jsonl"))
        for line in path.read_text().splitlines()
        if line.strip()
    ]
    raw = pd.DataFrame(rows)
    created = pd.to_datetime(raw["created_at"], utc=True)
    df = pd.DataFrame(
        {
            "repo": raw["repo"].str.split("/").str[1],
            "language": raw["repo"].map(language_of),
            "number": raw["number"],
            "title": raw["title"],
            "text": raw["title"] + ". " + raw["body"].map(clean_body),
            "state": raw["state"],
            "year": created.dt.year.astype(str),
            "created_at": created,
            "closed_at": pd.to_datetime(raw["closed_at"], utc=True),
            "comments": raw["comments"],
            "reactions": raw["reactions"],
            "labels": raw["labels"].map(", ".join),
            "url": raw["html_url"],
        }
    )
    df = compute_projection(
        df,
        inputs="text",
        modality="text",
        embedder="sentence-transformers",
        model="all-MiniLM-L6-v2",
        cache_root=DATA / ".cache",
    )
    df["twin"] = find_twins(df)
    out = DATA / "issues.parquet"
    tmp = out.with_suffix(".tmp")
    df[COLUMNS].to_parquet(tmp, index=False)
    tmp.replace(out)
    print(f"{len(df):,} issues, {int(df['twin'].notna().sum())} with an older R twin -> {out}")


if __name__ == "__main__":
    main()
