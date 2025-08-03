import subprocess
import webbrowser
from edenredtools.system.platform import System


class Browser:
    def open(self, url: str) -> None:
        if System.is_wsl():
            subprocess.run(["cmd.exe", "/c", "start", "", url.replace("&", "^&")])
        else:
            webbrowser.open(url)