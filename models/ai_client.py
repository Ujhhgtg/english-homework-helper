from openai import OpenAI


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
