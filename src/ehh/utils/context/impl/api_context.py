import httpx


from ..base import Context, Messenger


class APIContext(Context):
    def __init__(self, messenger: Messenger, http_client: httpx.Client) -> None:
        super().__init__(messenger)
        self.http_client = http_client
