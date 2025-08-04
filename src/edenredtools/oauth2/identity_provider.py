from abc import ABC, abstractmethod
from typing import Optional

import requests
from edenredtools.net.url import Url


class Oauth2IdentityProvider(ABC):
    @abstractmethod
    def token_url(self) -> Url: ...
    
    @abstractmethod
    def authorize_url(self) -> Url: ...
    
    
class OidcIdentityProvider(Oauth2IdentityProvider):
    def __init__(self, base_url: Url, session: Optional[requests.Session] = None) -> None:
        """
        :param base_url: Base URL of the IdP (e.g., https://accounts.google.com)
        :param session: Optional session object for connection reuse or mocking in tests.
        """
        self.base_url = base_url.normalize_path()
        self._session = session or requests.Session()
        self._discovery_doc = self._fetch_discovery_doc()

    def _fetch_discovery_doc(self) -> dict:
        """Retrieve the OpenID Connect discovery document."""
        discovery_url = self.base_url.join("/.well-known/openid-configuration")
        response = self._session.get(str(discovery_url), timeout=5)
        response.raise_for_status()
        return response.json()

    def token_url(self) -> Url:
        """Return the token endpoint from the discovery document."""
        return Url.from_string(self._discovery_doc.get("token_endpoint"))

    def authorize_url(self) -> Url:
        """Return the authorization endpoint from the discovery document."""
        return Url.from_string(self._discovery_doc.get("authorization_endpoint"))
