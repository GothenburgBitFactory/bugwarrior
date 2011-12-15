import time
from decorator import decorator


class rate_limit(object):
    """ API Rate Throttling decorator """
    def __init__(self, limit_amount, limit_period):
        self.limit_amount = limit_amount
        self.limit_period = limit_period
        self.start = time.time()
        self.counter = 0

    def __call__(self, func):
        def _rate_limit(*args, **kw):
            if time.time() - self.start > self.limit_period:
                self.start, self.counter = time.time(), 0

            self.counter += 1

            if self.counter == self.limit_amount - 1:
                duration = self.limit_period - (time.time() - self.start) + 1
                print "Expected to exceed API rate limit."
                print "Sleeping for", duration, "seconds."
                time.sleep(duration)

            return func(*args, **kw)

        return _rate_limit
