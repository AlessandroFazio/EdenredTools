from datetime import datetime as dt, timedelta
import datetime


class TokenValidator:
    @staticmethod
    def is_valid(token_data: dict, buffer_seconds) -> bool:
        """
        Returns True if token is still valid for at least `buffer_seconds`.
        """
        
        def expired(expiration: dt) -> bool:
            return dt.now(datetime.timezone.utc) + timedelta(seconds=buffer_seconds) < expiration
        
        if "access_token" not in token_data:
            return False

        if "expires_at" in token_data:
            try:
                return expired(dt.fromisoformat(token_data["expires_at"]))
            except ValueError:
                return False

        if "expires_in" in token_data and "issued_at" in token_data:
            try:
                issued_at = dt.fromisoformat(token_data["issued_at"])
                expires_in = int(token_data["expires_in"])
                return expired(issued_at + timedelta(seconds=expires_in))
            except (ValueError, TypeError):
                return False

        return False