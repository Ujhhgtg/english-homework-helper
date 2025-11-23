from typing import Optional

import httpx

try:
    from whisper.model import Whisper  # type: ignore
except ImportError:

    class Whisper: ...


from munch import Munch
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support.ui import WebDriverWait

from .messenger import Messenger


class Context:
    def __init__(self, messenger: Messenger) -> None:
        self.messenger = messenger
        self.config: Munch = None  # type: ignore
        self.whisper_model: Optional[Whisper] = None
        self.http_client: httpx.Client = httpx.Client(timeout=30)


class BrowserContext(Context):
    driver: WebDriver
    wait: WebDriverWait

    def __init__(self, messenger: Messenger) -> None:
        super().__init__(messenger)

    def init_driver(self, driver: WebDriver) -> None:
        self.driver = driver
        self.wait = WebDriverWait(self.driver, 15)


class APIContext(Context):
    def __init__(self, messenger: Messenger, http_client: httpx.Client) -> None:
        super().__init__(messenger)
        self.http_client = http_client
