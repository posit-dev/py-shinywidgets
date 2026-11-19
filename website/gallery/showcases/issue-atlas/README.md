# The Shiny issue atlas

6,088 GitHub issues from 9 Shiny-ecosystem repos (R and Python Shiny, bslib, htmltools,
shinywidgets, shinychat, shinytest2, shinydashboard, Shiny Server), embedded with
`all-MiniLM-L6-v2` and projected to 2D with embedding-atlas. Issues that ask for the same
thing cluster together -- including across languages, so a 2024 py-shiny issue can sit right
next to the 2015 R Shiny issue that asked first (the sidebar's "Asked twice" list surfaces
those pairs for whatever region you select).

This is a runnable example rather than a listed gallery page: it needs a WebGPU-capable
browser for the map, and the "Summarize selection" button makes live Claude calls
(`ANTHROPIC_API_KEY` required; the button explains itself when the key is unset).

```sh
uv run shiny run app.py
```

On first run the app downloads `issues.parquet` (~3 MB) from
[cpsievert/py-shinywidgets-data](https://github.com/cpsievert/py-shinywidgets-data/releases/tag/showcase-v1).

## Rebuilding the data

```sh
uv run python prep_data.py   # gh api -> data/raw/*.jsonl (needs the GitHub CLI)
uv run --no-project --python 3.12 --with embedding-atlas --with sentence-transformers \
    --with umap-learn --with pyarrow python embed.py   # -> data/issues.parquet
```

`embed.py` downloads the embedding model on first run and caches projections under
`data/.cache/`.
