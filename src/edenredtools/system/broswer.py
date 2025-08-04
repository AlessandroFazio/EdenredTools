import subprocess
import webbrowser
from edenredtools.system.platform import Platform


class Browser:
    def open(self, url: str) -> None:
        if Platform.is_wsl():
            subprocess.run(["cmd.exe", "/c", "start", "", url.replace("&", "^&")])
        else:
            webbrowser.open(url)