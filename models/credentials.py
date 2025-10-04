from dataclasses import dataclass

from utils.convert import mask_string_middle


@dataclass
class Credentials:
    """Represents user credentials."""

    school: str
    username: str
    password: str

    def describe(self) -> str:
        return f"{self.school} / {self.username} / {mask_string_middle(self.password)}"
