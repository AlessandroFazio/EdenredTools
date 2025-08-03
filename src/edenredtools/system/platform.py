import functools
import platform
from typing import Any, Callable, Dict, Type, TypeVar


T = TypeVar('T')


class System:
    SUPPORTED_PLATFORMS = ["Windows", "Linux", "Darwin"]
    _PLATFORM = platform.system()
    if _PLATFORM not in SUPPORTED_PLATFORMS:
        raise SystemError("")

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


def platform_dependent(* _, **kwargs: Dict[str, Any]) -> Callable[[Type[T]], Callable[..., T]]:
    def decorator(cls: Type[T]) -> Callable[..., T]:
        plat = System.get_platform()
        resolved_kwargs = {param: platform_map[plat] for param, platform_map in kwargs.items()}
        return functools.partial(cls, **resolved_kwargs)
    return decorator