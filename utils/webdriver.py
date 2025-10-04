from selenium.webdriver import Firefox
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement


class FirefoxDriver(Firefox):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def safe_find_element(
        self, by=By.ID, value: str | None = None
    ) -> WebElement | None:
        try:
            return self.find_element(by, value)
        except:
            return None
