from edenredtools.system.broswer import Browser
from edenredtools.system.dns import LocalDnsResolver
from edenredtools.system.networking import LinuxNetworking, LocalNetworking, WindowsNetworking
from edenredtools.system.platform import Platform


class SystemRegistry:
    _instance = None
    _dns_resolver: LocalDnsResolver = None
    _networking: LocalNetworking = None
    _browser: Browser = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        self._browser = Browser()
        system = Platform.get_platform()
        if system == "linux":
            self._dns_resolver = LocalDnsResolver("/etc/hosts")
            self._networking = LinuxNetworking()
        elif system == "windows":
            self._dns_resolver = LocalDnsResolver("C:\\Windows\\System32\\drivers\\etc\\hosts")
            self._networking = WindowsNetworking()
        else:
            raise NotImplementedError(f"No networking implementation for platform: {system}")

    @property
    def networking(self) -> LocalNetworking:
        return self._networking

    @property
    def dns_resolver(self) -> LocalDnsResolver:
        return self._dns_resolver

    @property
    def broswer(self) -> LocalDnsResolver:
        return self._browser
