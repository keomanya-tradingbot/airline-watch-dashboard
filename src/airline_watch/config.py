from __future__ import annotations

from pathlib import Path

import yaml

from .models import Source


def load_sources(path: Path) -> list[Source]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return [Source.model_validate(item) for item in raw.get("sources", [])]

