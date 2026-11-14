from dataclasses import dataclass
from typing import Any


@dataclass
class RetrievedDocument:
    id: str
    score: float
    text: str
    metadata: dict[str, Any]