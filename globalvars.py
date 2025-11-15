import whisper
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.remote.webdriver import WebDriver
from munch import Munch
import httpx

from utils.context.context import Context

driver: WebDriver = None  # type: ignore
wait: WebDriverWait = None  # type: ignore
whisper_model: whisper.model.Whisper | None = None
config: Munch = None  # type: ignore
context: Context = None  # type: ignore
http_client: httpx.Client = None  # type: ignore
