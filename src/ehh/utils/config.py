import json

import json5
from munch import Munch, munchify


def load_config(path: str = "local/config.json") -> Munch:
    with open(path, "rt", encoding="utf-8") as f:
        return munchify(json5.load(f))  # type: ignore


def save_config(config: Munch, path: str = "local/config.json") -> None:
    with open(path, "wt", encoding="utf-8") as f:
        f.write(json.dumps(config, indent=4, ensure_ascii=False))
