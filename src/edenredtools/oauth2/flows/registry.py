from abc import ABC, abstractmethod
import threading
from typing import Dict, Optional

from edenredtools.oauth2.flows.authorization import Oauth2AuthorizationFlow
from edenredtools.system.url import Url


class FlowState:
    def __init__(self):
        self._lock = threading.Condition()
        self._completed = False
        self._error: Optional[Exception] = None
        self._initiator_thread_id = threading.get_ident()
        self._flow: Optional[Oauth2AuthorizationFlow] = None
        
    def in_error(self) -> bool:
        return bool(self._error)

    def is_initiator(self) -> bool:
        return threading.get_ident() == self._initiator_thread_id

    def mark_done(self) -> None:
        with self._lock:
            self._completed = True
            self._lock.notify_all()

    def mark_error(self, err: Exception) -> None:
        with self._lock:
            self._error = err
            self._completed = True
            self._lock.notify_all()

    def wait_for_flow(self, timeout: float = 60.0) -> None:
        with self._lock:
            if not self._completed:
                self._lock.wait(timeout=timeout)
                
    def set_flow(self, flow: Oauth2AuthorizationFlow) -> None:
        self._flow = flow

    def get_flow(self) -> Optional[Oauth2AuthorizationFlow]:
        return self._flow


class AuthorizationFlowRegistry(ABC):
    @abstractmethod
    def get_or_create(self, authorize_url: Url) -> FlowState: ...

    @abstractmethod
    def get(self, authorize_url: Url) -> Optional[FlowState]: ...

    @abstractmethod
    def mark_done(self, authorize_url: Url) -> None: ...

    @abstractmethod
    def mark_error(self, authorize_url: Url, err: Exception) -> None: ...


class ThreadSafeAuthorizationFlowRegistry(AuthorizationFlowRegistry):
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._flows: Dict[Url, FlowState] = {}

    def get_or_create(self, authorize_url: Url) -> FlowState:
        with self._lock:
            state = self._flows.get(authorize_url)
            if not state:
                state = FlowState()
                self._flows[authorize_url] = state
            return state
        
    def get(self, authorize_url: Url) -> Optional[FlowState]:
        with self._lock:
            return self._flows.get(authorize_url)

    def mark_done(self, authorize_url: Url) -> None:
        with self._lock:
            state = self._flows.pop(authorize_url, None)
        if state:
            state.mark_done()

    def mark_error(self, authorize_url: Url, err: Exception) -> None:
        with self._lock:
            state = self._flows.pop(authorize_url, None)
        if state:
            state.mark_error(err)
