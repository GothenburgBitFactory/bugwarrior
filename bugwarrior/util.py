import time
from decorator import decorator


_start, _counter = time.time(), 0


@decorator
def rate_limit(func, *args, **kw):
    global _start, _counter

    # No more than 60 api calls in a minute
    limit_amount = 60  # API calls
    limit_period = 60  # seconds

    if time.time() - _start > limit_period:
        _start, _counter = time.time(), 0

    _counter += 1

    if _counter == limit_amount - 1:
        duration = limit_period - (time.time() - _start) + 1
        print "Expected to exceed API rate limit.  Sleeping for", duration
        time.sleep(duration)

    return func(*args, **kw)
