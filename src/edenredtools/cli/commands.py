from abc import ABC, abstractmethod
import sys

import click

from edenredtools.oauth2.flows.registry import ThreadSafeAuthorizationFlowRegistry
from edenredtools.oauth2.proxies import FlaskOauth2LocalProxy, Oauth2LocalProxyConfig
from edenredtools.oauth2.tokens.registry import ThreadSafeOauth2TokenRegistry
from edenredtools.system.dns import LocalDnsResolver
from edenredtools.system.platform import System


class CliCommand(ABC):
    def __call__(self) -> None:
        try:
            self.validate()
            self.execute()
        except Exception as e:
            self.handle_error(e)

    @abstractmethod
    def execute(self) -> None: ...
    
    @abstractmethod
    def validate(self) -> None: ...

    def handle_error(self, e: Exception) -> None:
        click.secho(f"[ERROR] {str(e)}", fg="red", err=True)
        sys.exit(1)


class Oauth2LocalProxyCommand(CliCommand):
    def __init__(
        self, 
        callback_hostname: str, 
        proxy_port: int, 
        callback_path: str,
        authorize_flow_timeout: int,
        ensure_dns_mapping: bool,
    ) -> None:
        self.callback_hostname = callback_hostname
        self.proxy_port = proxy_port
        self.callback_path = callback_path
        self.authorize_flow_timeout = authorize_flow_timeout
        self.ensure_dns_mapping = ensure_dns_mapping
        
    def validate(self) -> None:
        if self.ensure_dns_mapping and System.is_wsl():
            raise ValueError("could not modify local dns register on Windows host.")
    
    def execute(self) -> None:
        if self.ensure_dns_mapping:
            LocalDnsResolver().add_mapping(("127.0.0.1", self.callback_hostname))

        FlaskOauth2LocalProxy(
            ThreadSafeOauth2TokenRegistry(),
            ThreadSafeAuthorizationFlowRegistry(),
            Oauth2LocalProxyConfig(
                hostname=self.callback_hostname,
                port=self.proxy_port,
                callback_path=self.callback_path,
                authorize_flow_timeout=self.authorize_flow_timeout
            )
        ).start()