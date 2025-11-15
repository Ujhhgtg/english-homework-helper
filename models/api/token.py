from dataclasses import dataclass

from models.api.user_info import UserInfo


@dataclass
class Token:
    access_token: str
    token_type: str
    refresh_token: str
    expires_in: int
    scope: str
    jti: str
    user_info: UserInfo
