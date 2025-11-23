from rich.console import Console as RichConsole
from rich.highlighter import ReprHighlighter as RichHighlighter
from rich.theme import Theme as RichTheme
from rich.table import Table as RichTable
from rich.progress import Progress as RichProgress
from textual.widgets import RichLog as TextualLog
from textual.app import App as TextualApp
from textual.css.query import NoMatches


class Messenger:
    def send_text(self, *args, **kwargs) -> None:
        raise NotImplementedError

    def send_table(self, *args, **kwargs) -> None:
        raise NotImplementedError

    def send_progress(self, *args, **kwargs) -> None:
        raise NotImplementedError

    def send_exception(self, exception: Exception) -> None:
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

    def send_table(
        self,
        title: str,
        columns: list[tuple[str, str, str] | tuple[str, str]],
        rows: list[tuple],
        show_header: bool = True,
        header_style: str = "bold green",
    ):
        table = RichTable(
            title=title, show_header=show_header, header_style=header_style
        )

        for column in columns:
            try:
                justify = column[2]  # type: ignore
            except IndexError:
                justify = "left"
            table.add_column(
                column[0],
                style=column[1],
                justify=justify,  # type: ignore
            )

        for row in rows:
            table.add_row(*row)

        self.rich_console.print(table)

    def send_progress(self, func, *args, **kwargs):
        with RichProgress(console=self.rich_console) as progress:
            func(progress, *args, **kwargs)

    def send_exception(self, exception: Exception) -> None:
        self.rich_console.print_exception(exception, show_locals=True)  # type: ignore


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

    def send_progress(self, func, *args, **kwargs) -> None:
        func(None, *args, **kwargs)


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
