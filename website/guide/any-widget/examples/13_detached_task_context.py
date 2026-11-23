# A detached asyncio.create_task() inherits the live reactive context (it
# copies the current contextvars), so a reactive read inside the task
# registers the spawning effect as a dependent -- and the effect re-runs
# even though its body never read that value. Run: python 13_detached_task_context.py
import asyncio

from shiny import reactive

val = reactive.value(0)
runs = 0


@reactive.effect
def _():
    global runs
    runs += 1

    async def reader():
        # Registers the *effect's* context as a dependent of `val`, even
        # though the effect body never reads `val`.
        val()

    asyncio.create_task(reader())


async def main():
    await reactive.flush()
    await asyncio.sleep(0.1)  # let the detached task run
    assert runs == 1, runs
    val.set(1)  # nothing the effect does depends on val ...
    await reactive.flush()
    print(f"effect runs after unrelated val.set(): {runs} (expected 1)")


asyncio.run(main())
# Prints: effect runs after unrelated val.set(): 2 (expected 1)
