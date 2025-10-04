from rich.console import Console
from rich.highlighter import ReprHighlighter
from rich.theme import Theme

rich_console: Console | None = None


def print(*args, **kwargs):
    global rich_console
    if not rich_console:
        highlighter = ReprHighlighter()
        highlighter.highlights.extend(
            [
                r"(?i)\<(?P<debug>debug)\>",
                r"(?i)\<(?P<success>success)\>",
                r"(?i)\<(?P<info>info)\>",
                r"(?i)\<(?P<warning>warning)\>",
                r"(?i)\<(?P<error>error)\>",
            ]
        )
        theme = Theme(
            {
                "repr.debug": "dim",
                "repr.success": "bold green",
                "repr.info": "bold blue",
                "repr.warning": "bold yellow",
                "repr.error": "bold red",
            }
        )
        rich_console = Console(highlighter=highlighter, theme=theme)
    rich_console.print(*args, **kwargs)
