from abc import ABC, abstractmethod
import sys

import click

from edenredtools.oauth2.flows.registry import ThreadSafeAuthorizationFlowRegistry
from edenredtools.oauth2.proxies import FlaskOauth2LocalProxy, Oauth2LocalProxyConfig
from edenredtools.oauth2.tokens.registry import ThreadSafeOauth2TokenRegistry
from edenredtools.system.dns import LocalDnsResolver
from edenredtools.system.registry import SystemRegistry
from edenredtools.system.url import Url


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
        callback_url: str, 
        proxy_port: int,
        authorize_flow_timeout: int,
        autoconfigure_system: bool,
    ) -> None:
        self.callback_url = Url.from_string(callback_url)
        self.proxy_port = proxy_port
        self.authorize_flow_timeout = authorize_flow_timeout
        self.autoconfigure_system = autoconfigure_system

    def execute(self) -> None:
        system = SystemRegistry()
        if self.autoconfigure_system: 
            self._autoconfigure_system(system)

        FlaskOauth2LocalProxy(
            system,
            ThreadSafeOauth2TokenRegistry(),
            ThreadSafeAuthorizationFlowRegistry(),
            Oauth2LocalProxyConfig(
                callback_url=self.callback_url,
                port=self.proxy_port,
                authorize_flow_timeout=self.authorize_flow_timeout
            )
        ).start()
        
    def _autoconfigure_system(self, system: SystemRegistry) -> None:
        # DNS auto configuration
        system.dns_resolver.add_mapping(("127.0.0.1", self.callback_url))

        # ip forwarding auto configuration
        src_port, dst_port = self.callback_url.port(), self.proxy_port
        if src_port != dst_port:
            system.networking.configure_ip_forwarding(src_port, dst_port)