from dataclasses import dataclass
from typing import Optional

from pydantic import BaseModel, HttpUrl

from edenredtools.net.url import Url


@dataclass
class Oauth2LocalProxyConfig:
    port: int
    authorize_flow_timeout: int
    autoconfigure_system: bool
    fingerprint_secret: str


class LocalProxyTokenRequest(BaseModel):
    authorize_url: HttpUrl
    callback_url: HttpUrl
    client_secret: Optional[str] = None
    
    
    