from openai import OpenAI
from munch import Munch

from utils.convert import mask_string_middle


class AIClient:
    api_url: str
    api_key: str
    model: str
    client: OpenAI

    def __init__(self, api_url: str, api_key: str, model: str):
        self.api_url = api_url
        self.api_key = api_key
        self.model = model
        self.client = OpenAI(api_key=self.api_key, base_url=self.api_url)

    @classmethod
    def from_dict(cls, data: Munch):
        return cls(data.api_url, data.api_key, data.model)

    def describe(self) -> str:
        return f"{self.api_url} / {mask_string_middle(self.api_key)} / {self.model}"
