# Shiny Express can run a sibling globals.py more than once per process (once
# to build the page, again when a session connects) -- unlike plain `import`,
# which Python would cache. DuckDB's `lock_configuration` can only be set
# once per process; setting it again raises. So the lockdown below checks
# first and is a no-op the second time, which is what makes it safe to put
# here at all. Never do this lockdown inline in an Express app file: it would
# run on every execution with no way to check first, and crash the first
# session that connects after the page itself has already run it once. See
# "Security and privacy" in the guide for what this protects against.
import duckdb
import pygwalker

# PyGWalker otherwise phones home from both the Python process and every
# visitor's browser
pygwalker.GlobalVarManager.set_privacy("offline")

already_locked = duckdb.execute(
    "SELECT current_setting('lock_configuration')"
).fetchone()[0]
if not already_locked:
    # Set first: PyGWalker sets it per query, which a locked configuration refuses
    duckdb.execute("SET TimeZone = 'UTC'")
    duckdb.execute("SET enable_external_access = false")
    duckdb.execute("SET lock_configuration = true")
