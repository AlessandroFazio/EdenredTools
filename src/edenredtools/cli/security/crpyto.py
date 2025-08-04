import base64
import hmac
import hashlib
import secrets


class CryptoUtils:
    @staticmethod
    def compute_fingerprint(secret: str, string: str) -> str:
        return hmac.new(
            secret.encode("utf-8"), 
            string.encode("utf-8"), 
            hashlib.sha256
        ).hexdigest()
    
    @staticmethod
    def generate_secret_key(num_bytes: int = 32) -> str:
        """
        Generates a cryptographically secure random secret and returns it as a base64 string.
        """
        return base64.urlsafe_b64encode(secrets.token_bytes(num_bytes)).decode("utf-8")