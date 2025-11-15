from dataclasses import dataclass
from munch import Munch

from utils.convert import mask_string_middle


@dataclass
class Credentials:
    school: str
    username: str
    password: str

    @classmethod
    def from_dict(cls, data: Munch):
        return cls(data.school, data.username, data.password)

    def describe(self) -> str:
        return f"{self.school} / {self.username} / {mask_string_middle(self.password)}"
