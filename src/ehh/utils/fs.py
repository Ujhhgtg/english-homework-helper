from pathlib import Path

from platformdirs import PlatformDirs

PLATFORM_DIRS = PlatformDirs(appname="ehh", appauthor="ujhhgtg", ensure_exists=True)

CONFIG_DIR = Path(PLATFORM_DIRS.user_config_dir)
CACHE_DIR = Path(PLATFORM_DIRS.user_cache_dir)


def read_file_text(path: str | Path) -> str:
    with open(path, "rt", encoding="utf-8") as f:
        return f.read()
