# From https://gist.github.com/jcheng5/427de09573816c4ce3a8c6ec1839e7c0
import functools
import time

from shiny import reactive


def debounce(delay_secs):
    def wrapper(f):
        when = reactive.Value(None)
        trigger = reactive.Value(0)

        @reactive.Calc
        def cached():
            """
            Just in case f isn't a reactive calc already, wrap it in one. This ensures
            that f() won't execute any more than it needs to.
            """
            return f()

        @reactive.Effect(priority=102)
        def primer():
            """
            Whenever cached() is invalidated, set a new deadline for when to let
            downstream know--unless cached() invalidates again
            """
            try:
                cached()
            except Exception:
                ...
            finally:
                when.set(time.time() + delay_secs)

        @reactive.Effect(priority=101)
        def timer():
            """
            Watches changes to the deadline and triggers downstream if it's expired; if
            not, use invalidate_later to wait the necessary time and then try again.
            """
            deadline = when()
            if deadline is None:
                return
            time_left = deadline - time.time()
            if time_left <= 0:
                # The timer expired
                with reactive.isolate():
                    when.set(None)
                    trigger.set(trigger() + 1)
            else:
                reactive.invalidate_later(time_left)

        @reactive.Calc
        @reactive.event(trigger, ignore_none=False)
        @functools.wraps(f)
        def debounced():
            return cached()

        return debounced

    return wrapper


def throttle(delay_secs):
    def wrapper(f):
        last_signaled = reactive.Value(None)
        last_triggered = reactive.Value(None)
        trigger = reactive.Value(0)

        @reactive.Calc
        def cached():
            return f()

        @reactive.Effect(priority=102)
        def primer():
            try:
                cached()
            except Exception:
                ...
            finally:
                last_signaled.set(time.time())

        @reactive.Effect(priority=101)
        def timer():
            if last_triggered() is not None and last_signaled() < last_triggered():
                return

            now = time.time()
            if last_triggered() is None or (now - last_triggered()) >= delay_secs:
                last_triggered.set(now)
                with reactive.isolate():
                    trigger.set(trigger() + 1)
            else:
                reactive.invalidate_later(delay_secs - (now - last_triggered()))

        @reactive.Calc
        @reactive.event(trigger, ignore_none=False)
        @functools.wraps(f)
        def throttled():
            return cached()

        return throttled

    return wrapper
