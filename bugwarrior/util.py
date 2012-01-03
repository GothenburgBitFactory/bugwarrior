from twiggy import log

import time


class rate_limit(object):
    """ API Rate Throttling decorator """
    def __init__(self, limit_amount, limit_period):
        self.limit_amount = limit_amount
        self.limit_period = limit_period
        rate_limit.start = time.time()
        rate_limit.counter = 0

    def __call__(self, func):
        def _rate_limit(*args, **kw):
            if time.time() - rate_limit.start > self.limit_period:
                rate_limit.start, rate_limit.counter = time.time(), 0

            rate_limit.counter += 1

            if rate_limit.counter == self.limit_amount - 1:
                duration = self.limit_period - \
                        (time.time() - rate_limit.start) + 1
                log.warning("Expected to exceed API rate limit. Sleeping {0}s",
                        duration)
                time.sleep(duration)

            return func(*args, **kw)

        return _rate_limit
