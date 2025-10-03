from dataclasses import dataclass


@dataclass
class Credentials:
    """Represents user credentials."""

    school: str
    username: str
    password: str
