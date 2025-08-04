import platform
from typing import TypeVar


T = TypeVar('T')


class Platform:
    SUPPORTED_PLATFORMS = ["windows", "linux"]
    _PLATFORM = platform.system().lower()
    if _PLATFORM not in SUPPORTED_PLATFORMS:
        raise SystemError(f"platform '{_PLATFORM}' is not supported. Supported: {SUPPORTED_PLATFORMS}")

    @classmethod
    def get_platform(cls) -> str:
        return cls._PLATFORM
    
    @classmethod
    def is_wsl(cls) -> bool:
        try:
            with open("/proc/sys/kernel/osrelease") as f:
                osrelease = f.read().lower()
            return "microsoft" in osrelease and "wsl2" in osrelease
        except FileNotFoundError:
            return False