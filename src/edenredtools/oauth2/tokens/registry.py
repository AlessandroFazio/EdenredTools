from abc import ABC, abstractmethod
import threading
from typing import Dict, Optional

from edenredtools.oauth2.tokens.validator import TokenValidator
from edenredtools.system.url import Url


class Oauth2TokenRegistry(ABC):
    @abstractmethod
    def get(self, authorize_url: Url): ...

    @abstractmethod
    def set(self, authorize_url: Url, token_data: dict): ...

    @abstractmethod
    def read_valid_token(self, authorize_url: Url, buffer_seconds: int=10) -> Optional[dict]: ...


class ThreadSafeOauth2TokenRegistry(Oauth2TokenRegistry):
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._store: Dict[Url, dict] = {}

    def get(self, authorize_url: Url):
        with self._lock:
            return self._store.get(authorize_url)

    def set(self, authorize_url: Url, token_data: dict):
        with self._lock:
            self._store[authorize_url] = token_data

    def read_valid_token(self, authorize_url: Url, buffer_seconds: int=10) -> Optional[dict]:
        token = self.get(authorize_url)
        if not token:
            return None
        if not TokenValidator.is_valid(token, buffer_seconds):
            return None
        return token 