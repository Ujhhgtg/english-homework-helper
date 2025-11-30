from textual.widgets import RichLog
from textual.app import App
from textual.css.query import NoMatches

from ..base import Messenger


class TextualMessenger(Messenger):
    def __init__(self, app: App, widget_id: str) -> None:
        self.app = app
        self.widget_id = widget_id
        super().__init__()

    def send_text(self, *args, **kwargs):
        try:
            log_widget = self.app.query_one("#output-log", RichLog)
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
