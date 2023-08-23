from limits import storage, strategies, parse

_SHARED_TOKEN = "shared"


class RateLimiter:
    def __init__(self, rate: str):
        # using in-memory storage here to reduce dependencies
        memory_storage = storage.MemoryStorage()
        self._limiter = strategies.MovingWindowRateLimiter(storage=memory_storage)
        self._item = parse(rate)

    def hit(self, token=_SHARED_TOKEN) -> bool:
        return self._limiter.hit(self._item, token, cost=1)
