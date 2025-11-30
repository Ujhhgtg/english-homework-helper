from .cli_api import main as cli_api

try:
    from .cli_browser import main as cli_browser
except ImportError:
    cli_browser = lambda: print(
        "cli_browser is not available. ensure all dependencies are installed."
    )
try:
    from .tui import main as tui
except ImportError:
    tui = lambda: print("tui is not available. ensure all dependencies are installed.")
try:
    from .telegram_bot import main as telegram_bot
except ImportError:
    telegram_bot = lambda: print(
        "telegram_bot is not available. ensure all dependencies are installed."
    )

__all__ = ["cli_api", "cli_browser", "tui", "telegram_bot"]
