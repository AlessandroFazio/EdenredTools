from abc import abstractmethod
import re
import subprocess


class LocalNetworking:    
    @abstractmethod 
    def check_ip_forwarding_exists(
        self, 
        src_port: int, 
        dst_port: int, 
        src_address: str, 
        dst_address: str
    ) -> bool: ...
    
    @abstractmethod
    def add_ip_forwarding_rule(
        self, 
        src_port: int, 
        dst_port: int, 
        src_address: str, 
        dst_address: str
    ) -> None: ...
    
    @abstractmethod
    def enable_ip_forwarding(self) -> None: ...
    
    @abstractmethod
    def check_enabled_ip_forwarding(self) -> None: ...
    
    def configure_ip_forwarding(
        self, 
        src_port: int, 
        dst_port: int, 
        src_address: str="0.0.0.0", 
        dst_address: str="127.0.0.1"
    ) -> None:
        if self.check_enabled_ip_forwarding():
            print("IP port forwarding already enabled")
        else:
            print("Enabling IP port forwarding")
            self.enable_ip_forwarding()
        
        if self.check_ip_forwarding_exists(src_port, dst_port, src_address, dst_address):
            print(f"Rule already exists: {src_port} → {dst_port}")
            return
        
        print(f"Adding rule: {src_port} → {dst_port}")
        self.add_ip_forwarding_rule(src_port, dst_port, src_address, dst_address)

        
class LinuxNetworking(LocalNetworking):
    def enable_ip_forwarding() -> None:
        subprocess.run(["sysctl", "-w", "net.ipv4.ip_forward=1"], check=True)
    
    def check_ip_forwarding_exists(
        self, 
        src_port: int, 
        dst_port: int, 
        src_address: str, 
        dst_address: str
    ) -> bool:
        cmd = [
            "iptables", "-t", "nat", "-C", "PREROUTING",
            "-p", "tcp", "-d", dst_address, "-s", src_address, "--dport", str(src_port),
            "-j", "REDIRECT", "--to-port", str(dst_port)
        ]
        try:
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except subprocess.CalledProcessError:
            return False
        
    def add_ip_forwarding_rule(
        self, 
        src_port: int, 
        dst_port: int, 
        src_address: str, 
        dst_address: str
    ) -> None:
        cmd = [
            "iptables", "-t", "nat", "-A", "PREROUTING",
            "-p", "tcp", "-d", dst_address, "-s", src_address, "--dport", str(src_port),
            "-j", "REDIRECT", "--to-port", str(dst_port)
        ]
        subprocess.run(cmd, check=True)

    def check_enabled_ip_forwarding(self) -> None:
        result = subprocess.run(["sysctl", "net.ipv4.ip_forward"], check=True, capture_output=True, text=True)
        return bool(re.match(r'^net\.ipv4\.ip_forward\s*=\s*1$', result.stdout.strip()))
        
    def enable_ip_forwarding(self) -> None:
        subprocess.run(["sysctl", "-w", "net.ipv4.ip_forward=1"], check=True)


class WindowsNetworking(LocalNetworking):
    def enable_ip_forwarding(self) -> None:
        pass # NO-OP
    
    def check_enabled_ip_forwarding(self) -> bool:
        return True # NO-OP
    
    def check_ip_forwarding_exists(
        self,
        src_address: str,
        src_port: int,
        dest_address: str,
        dest_port: int
    ) -> bool:
        cmd = ["netsh", "interface", "portproxy", "show", "v4tov4"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        pattern = rf"{src_address}\s+{src_port}\s+{dest_address}\s+{dest_port}"
        return re.search(pattern, result.stdout) is not None

    def add_ip_forwarding_rule(
        self,
        src_address: str,
        src_port: int,
        dest_address: str,
        dest_port: int
    ) -> None:
        cmd = [
            "netsh", "interface", "portproxy", "add", "v4tov4",
            f"listenaddress={src_address}",
            f"listenport={src_port}",
            f"connectaddress={dest_address}",
            f"connectport={dest_port}"
        ]
        subprocess.run(cmd, check=True)
