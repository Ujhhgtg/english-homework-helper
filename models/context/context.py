from models.context.messenger import Messenger


class Context:
    def __init__(self, messenger: Messenger) -> None:
        self.messenger = messenger
