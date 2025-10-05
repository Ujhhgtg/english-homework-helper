import whisper
from prompt_toolkit import PromptSession
from selenium.webdriver.support.ui import WebDriverWait
from munch import Munch

from utils.webdriver import FirefoxDriver

driver: FirefoxDriver = None  # type: ignore
wait: WebDriverWait = None  # type: ignore
whisper_model: whisper.model.Whisper | None = None
config: Munch = None  # type: ignore
