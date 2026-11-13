# Data for the "Brushing large data" section

`gaia-5m.parquet` (not committed; see `.gitignore`) is the Gaia 5M sample from the
[Mosaic datasets](https://github.com/uwdata/mosaic-datasets) collection maintained by
the University of Washington Interactive Data Lab, fetched from:

```
http://idl.uw.edu/mosaic-datasets/data/gaia-5m.parquet
```

5,000,000 rows, 5 columns, derived from the [Gaia](https://www.cosmos.esa.int/web/gaia)
space mission's public catalog of stellar positions and brightness:

| Column | Meaning |
|---|---|
| `l` | Galactic longitude, degrees (0-360) |
| `b` | Galactic latitude, degrees (-90 to 90) |
| `parallax` | Parallax, milliarcseconds (noisy; a small fraction of rows are far outside a plausible range) |
| `phot_g_mean_mag` | Mean G-band magnitude (brightness; lower is brighter) |
| `bp_rp` | BP-RP color index (not used by these examples) |

Fetch it yourself with:

```sh
curl -sL -o gaia-5m.parquet http://idl.uw.edu/mosaic-datasets/data/gaia-5m.parquet
```

Used by `examples/18_datashader_brush_summaries.py`, `examples/19_scattergl_lasso_raw_points.py`,
and `examples/20_mosaic_brush_in_widget.py` -- the same dataset for all three, so the
"push summaries, not points" comparison holds the data fixed and varies only the
approach.
