from typing import Optional
from pydantic import BaseModel


class OAuth2AccessTokenResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: Optional[int] = None
    refresh_token: Optional[str] = None
    scope: Optional[str] = None
    id_token: Optional[str] = None