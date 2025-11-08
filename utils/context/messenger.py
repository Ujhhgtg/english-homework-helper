from rich.console import Console as RichConsole
from rich.highlighter import ReprHighlighter as RichHighlighter
from rich.theme import Theme as RichTheme
from textual.widgets import RichLog as TextualLog
from textual.app import App as TextualApp
from textual.css.query import NoMatches


class Messenger:
    def send_text(self, *args, **kwargs):
        raise NotImplementedError


class ConsoleMessenger(Messenger):
    def __init__(self) -> None:
        super().__init__()
        highlighter = RichHighlighter()
        highlighter.highlights.extend(
            [
                r"(?i)\<(?P<debug>debug)\>",
                r"(?i)\<(?P<success>success)\>",
                r"(?i)\<(?P<info>info)\>",
                r"(?i)\<(?P<warning>warning)\>",
                r"(?i)\<(?P<error>error)\>",
            ]
        )
        theme = RichTheme(
            {
                "repr.debug": "dim",
                "repr.success": "bold green",
                "repr.info": "bold blue",
                "repr.warning": "bold yellow",
                "repr.error": "bold red",
            }
        )
        self.rich_console = RichConsole(highlighter=highlighter, theme=theme)

    def send_text(self, *args, **kwargs):
        self.rich_console.print(*args, **kwargs)


class TelegramMessenger(Messenger):
    def __init__(self, bot, chat_id):
        self.bot = bot
        self.chat_id = chat_id

    def send_text(self, *args, **kwargs):
        format_mode = kwargs.get("format_mode")
        try:
            if format_mode is None:
                self.bot.send_message(chat_id=self.chat_id, text=args[0])
            else:
                self.bot.send_message(
                    chat_id=self.chat_id, text=args[0], format_mode=format_mode
                )
        except Exception as e:
            print(f"<error> failed to send Telegram message: {e}")


class TextualMessenger(Messenger):
    def __init__(self, app: TextualApp, widget_id: str) -> None:
        self.app = app
        self.widget_id = widget_id
        super().__init__()

    def send_text(self, *args, **kwargs):
        try:
            log_widget = self.app.query_one("#output-log", TextualLog)
        except NoMatches:
            print(
                f"<warning> could not following in app due to log widget not found:\n{args[0]}"
            )
            return

        message = (
            args[0]
            .replace("[", "[[")
            .replace("]", "]]")
            .replace("<info>", "<[blue]info[/blue]>")
            .replace("<error>", "<[red]error[/red]>")
            .replace("<warning>", "<[yellow]warning[/yellow]>")
            .replace("<success>", "<[b][green]success[/green][/b]>")
        )
        log_widget.write(message)
