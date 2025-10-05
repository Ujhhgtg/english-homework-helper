from utils.logging import print


class Messenger:
    """Abstract class/interface for handling output."""

    def send_message(self, *args, **kwargs):
        """Standard method for primary output."""
        raise NotImplementedError


class ConsoleMessenger(Messenger):
    def send_message(self, *args, **kwargs):
        """Prints output directly to the console."""
        print(*args, **kwargs)


class TelegramMessenger(Messenger):
    def __init__(self, bot, chat_id):
        self.bot = bot
        self.chat_id = chat_id

    def send_message(self, *args, **kwargs):
        """Sends a message via the Telegram API."""

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
