from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass
class RunLogger:
    output_dir: str
    jsonl_filename: str
    console: bool = True

    def __post_init__(self) -> None:
        self.path = Path(self.output_dir) / self.jsonl_filename
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def log(self, event: str, level: str = "INFO", **kwargs) -> None:
        payload = {
            "ts": datetime.utcnow().isoformat() + "Z",
            "level": level,
            "event": event,
        }
        payload.update(kwargs)

        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=True) + "\n")

        if self.console:
            compact = {"event": event, **kwargs}
            print(f"[{level}] {compact}")
