from typing import NamedTuple
from sentinel.core.collectors import disk

class FakeUsage(NamedTuple):
    total: int
    used: int
    free: int
