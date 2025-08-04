from abc import ABC, abstractmethod
import sys

import click

from edenredtools.oauth2.flows.registry import ThreadSafeAuthorizationFlowRegistry
from edenredtools.oauth2.proxies.local import FlaskOauth2LocalProxy
from edenredtools.oauth2.proxies.models import Oauth2LocalProxyConfig
from edenredtools.oauth2.tokens.registry import ThreadSafeOauth2TokenRegistry
from edenredtools.system.registry import SystemRegistry


class CliCommand(ABC):
    def __call__(self) -> None:
        try:
            self.validate()
            self.execute()
        except Exception as e:
            self.handle_error(e)

    @abstractmethod
    def execute(self) -> None: ...
    
    def validate(self) -> None:
        pass

    def handle_error(self, e: Exception) -> None:
        click.secho(f"[ERROR] {str(e)}", fg="red", err=True)
        sys.exit(1)


class Oauth2LocalProxyCommand(CliCommand):
    def __init__(
        self, 
        proxy_port: int,
        authorize_flow_timeout: int,
        autoconfigure_system: bool,
        fingerprint_secret: str
    ) -> None:
        self.proxy_port = proxy_port
        self.authorize_flow_timeout = authorize_flow_timeout
        self.autoconfigure_system = autoconfigure_system
        self.fingerprint_secret = fingerprint_secret

    def execute(self) -> None:
        FlaskOauth2LocalProxy(
            SystemRegistry(),
            ThreadSafeOauth2TokenRegistry(),
            ThreadSafeAuthorizationFlowRegistry(),
            Oauth2LocalProxyConfig(
                port=self.proxy_port,
                authorize_flow_timeout=self.authorize_flow_timeout,
                autoconfigure_system=self.autoconfigure_system,
                fingerprint_secret=self.fingerprint_secret
            )
        ).start()