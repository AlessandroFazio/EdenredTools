import re
from typing import List, Tuple

from edenredtools.system.platform import platform_dependent
from edenredtools.system.file import FileUtils


@platform_dependent(
    path = {
        "Linux": "/etc/hosts",
        "Darwin": "/etc/hosts",
        "Windows": "C:\Windows\System32\drivers\etc"
})
class LocalDnsResolver:
    _MAPPING_RE_PATTERN = r'^\s*(\d{1,3}(?:\.\d{1,3}){3})\s+([^\s#]+)'

    def __init__(self, path: str) -> None:
        self.path = path

    def get_mappings(self) -> List[Tuple[str, str]]:
        mappings = []
        with open(self.path) as f:
            for line in f.readlines():
                if line.startswith("#"):
                    continue
                match = re.match(self._MAPPING_RE_PATTERN, line)
                if match:
                    ip, hostname = match.groups()
                    mappings.append((ip, hostname))
        return mappings

    def add_mapping(self, mapping: Tuple[str, str]) -> bool:
        mappings = self.get_mappings()
        if mapping in mappings:
            return False

        ip, hostname = mapping
        with open(self.path, "a") as f:
            if not FileUtils.ends_with_newline(self.path):
                f.write("\n")
            f.write(f"### Edenred Auth Tools ###\n{ip} {hostname}\n")
        return True