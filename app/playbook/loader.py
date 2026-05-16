from pathlib import Path
from typing import Any

import yaml

from app.playbook.schemas import SalesPlaybook

DEFAULT_PLAYBOOK_PATH = Path("config/sales_playbook.yaml")


def load_playbook(path: str | Path = DEFAULT_PLAYBOOK_PATH) -> SalesPlaybook:
    playbook_path = Path(path)
    raw_data = yaml.safe_load(playbook_path.read_text(encoding="utf-8"))

    if not isinstance(raw_data, dict):
        raise ValueError(f"Playbook must be a YAML mapping: {playbook_path}")

    return SalesPlaybook.model_validate(raw_data)


def dump_playbook_data(playbook: SalesPlaybook) -> dict[str, Any]:
    return playbook.model_dump(mode="json")
