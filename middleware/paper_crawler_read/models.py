from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class Paper:
    title: str
    link: str
    pdf_url: Optional[str]
    snippet: Optional[str]
    authors: List[str]
    year: Optional[int]

