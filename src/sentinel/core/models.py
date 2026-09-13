from datetime import datetime
from typing import Any
from pydantic import BaseModel

class CheckResult(BaseModel):
    collector: str
    target: str | None = None
    timestamp: datetime
    metrics: dict[str, float | int | bool]
    details: dict[str, Any] = {}
    