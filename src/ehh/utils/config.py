import json
from pathlib import Path

import json5
from munch import Munch, munchify
from platformdirs import user_config_dir

from .logging import print

CONFIG_DIR = user_config_dir(appname="ehh", appauthor="ujhhgtg", ensure_exists=True)
CONFIG_FILE = str(Path(CONFIG_DIR) / "config.json")


def load_config(path: str = CONFIG_FILE) -> Munch:
    if not Path(path).exists():
        raise FileNotFoundError(
            f"Config file not found at {path}. Please create one based on config.json.example."
        )

    with open(path, "rt", encoding="utf-8") as f:
        return munchify(json5.load(f))  # type: ignore


def save_config(config: Munch, path: str = CONFIG_FILE) -> None:
    with open(path, "wt", encoding="utf-8") as f:
        f.write(json.dumps(config, indent=4, ensure_ascii=False))


def migrate_config_if_needed() -> None:
    old_config_path = "local/config.json"
    if Path(old_config_path).exists() and not Path(CONFIG_FILE).exists():
        config = load_config(old_config_path)
        save_config(config, CONFIG_FILE)
        Path(old_config_path).unlink()
        print("<info> migrated config to new location")
