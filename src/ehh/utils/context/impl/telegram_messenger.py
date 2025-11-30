from telegram.ext import ExtBot
from ..base import Messenger


class TelegramMessenger(Messenger):
    def __init__(self, bot: ExtBot, chat_id: str | int) -> None:
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
