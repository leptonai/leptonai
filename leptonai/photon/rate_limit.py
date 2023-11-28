from limits import storage, strategies, parse
from typing import Optional

_SHARED_TOKEN = "shared"


class RateLimiter:
    def __init__(self, rate: str, name: Optional[str] = None):
        # using in-memory storage here to reduce dependencies
        memory_storage = storage.MemoryStorage()
        self._name = name
        self._limiter = strategies.MovingWindowRateLimiter(storage=memory_storage)
        self._item = parse(rate)

    def hit(self, token=_SHARED_TOKEN) -> bool:
        return self._limiter.hit(self._item, token, cost=1)

    @property
    def name(self):
        return self._name
