## mols2grid app

What `@render_mols2grid` adds over a static table of molecules: a searchable,
sortable, paginated grid of chemical structures (drawn in the browser by RDKit)
whose selection you can read back reactively with `grid.selection`
(or as a DataFrame via `grid.grid.get_selection()`), and which you can filter from
Python — without re-rendering — with `grid.grid.filter(mask)`, as the sliders
in this app demonstrate.

Note that the grid's JavaScript loads from CDNs, so it requires an internet
connection.
