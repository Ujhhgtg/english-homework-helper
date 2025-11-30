from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support.ui import WebDriverWait

from ..base import Context, Messenger


class BrowserContext(Context):
    driver: WebDriver
    wait: WebDriverWait

    def __init__(self, messenger: Messenger) -> None:
        super().__init__(messenger)

    def init_driver(self, driver: WebDriver) -> None:
        self.driver = driver
        self.wait = WebDriverWait(self.driver, 15)
