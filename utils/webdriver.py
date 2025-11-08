from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement


def safe_find_element(driver, by=By.ID, value: str | None = None) -> WebElement | None:
    try:
        return driver.find_element(by, value)
    except:
        return None
