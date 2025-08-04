import base64
from dataclasses import dataclass, field, fields
import datetime
from datetime import datetime as dt
import hashlib
import random
import secrets
import string
from typing import Any, Dict, List, Optional

from flask import json
import requests

from edenredtools.oauth2.identity_provider import Oauth2IdentityProvider
from edenredtools.system.broswer import Browser
from edenredtools.system.url import Url


@dataclass
class Oauth2AuthorizeRequestParams:
    client_id: str
    scope: str
    redirect_uri: str
    response_type: str
    response_mode: Optional[str] = "query"
    state: str = ""
    code_verifier: Optional[str] = None
    code_challenge: Optional[str] = None
    code_challenge_method: Optional[str] = None
    extra: Dict[str, List[Any]] = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.client_id:
            raise ValueError("client_id must be set.")
        if not self.scope:
            raise ValueError("scope must be set.")
        if not self.redirect_uri:
            raise ValueError("redirect_uri must be set.")
        if not self.response_type:
            raise ValueError("response_type must be set.")
        if self.code_challenge_method:
            if self.code_challenge_method not in ["S256", "plain"]:
                raise ValueError("")
            self.code_verifier = self._generate_code_verifier()
            self.code_challenge = self._generate_code_challenge()
            
    def use_pkce(self) -> bool:
        return bool(self.code_challenge and self.code_challenge_method)
    
    def _generate_pcke(self) -> None:
        self.code_verifier = self._generate_code_verifier()
        self.code_challenge = self._generate_code_challenge()
    
    def _generate_code_verifier(self):
        charset = string.ascii_letters + string.digits + "-._~"
        return ''.join(secrets.choice(charset) for _ in range(random.randint(43,128)))

    def _generate_code_challenge(self) -> str:
        if self.code_challenge_method == "plain":
            return self.code_verifier
        elif self.code_challenge_method == "S256":
            digest = hashlib.sha256(self.code_verifier.encode('ascii')).digest()
            return base64.urlsafe_b64encode(digest).decode('ascii').rstrip("=")
        else:
            raise ValueError("")

    def to_query_params(self) -> Dict[str, List[Any]]:
        params: Dict[str, List[Any]] = {
            "client_id": [self.client_id],
            "scope": [self.scope],
            "redirect_uri": [self.redirect_uri],
            "response_type": [self.response_type],
        }
        if self.response_mode:
            params["response_mode"] = [self.response_mode]
        if self.state:
            params["state"] = [self.state]
        if self.use_pkce():
            params["code_challenge"] = [self.code_challenge]
            params["code_challenge_method"] = [self.code_challenge_method]
        
        for k, v in self.extra.items():
            params[k] = [v]
        
        return params
    
    @classmethod
    def transients(cls) -> List[str]:
        return ["code_challenge", "code_verifier", "state"]
    
    @classmethod
    def non_transients(cls) -> List[str]:
        return [f.name for f in fields(cls) if f.name not in cls.transients() + ["extra"]]
    
    @classmethod
    def from_authorize_url(cls, url: Url) -> "Oauth2AuthorizeRequestParams":
        flow_params = {}
        extra = {}
        for name, val in url.get_params().items():
            if name in cls.transients():
                continue
            elif name in cls.non_transients():
                flow_params[name] = val[0]
            else:
                extra[name] = val[0]
                
        raw = json.dumps({"authorize_url": str(url)}).encode("utf-8")
        state = base64.urlsafe_b64encode(raw).decode("utf-8")
        return cls(**flow_params, extra=extra, state=state)


class Oauth2AuthorizationFlow:
    def __init__(
        self, 
        identity_provider: Oauth2IdentityProvider, 
        authorize_params: Oauth2AuthorizeRequestParams,
        client_secret: Optional[str],
        browser: Browser
    ) -> None:
        self.identity_provider = identity_provider
        self.authorize_params = authorize_params
        self.client_secret = client_secret
        self.browser = browser
        self.validate()
        
    def validate(self) -> None:
        if not self.authorize_params.use_pkce() and not self.client_secret:
            raise ValueError("")
        
    def commence(self) -> None:
        authorize_url = self.identity_provider.authorize_url()
        query_params = self.authorize_params.to_query_params()
        url = str(authorize_url.with_params(**query_params))
        self.browser.open(url)
        
    def exchange_code(self, code: str, state: str) -> Dict[str, Any]:
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.authorize_params.redirect_uri,
            "client_id": self.authorize_params.client_id
        }
        if self.client_secret:
            data["client_secret"] = self.client_secret
        if self.authorize_params.code_verifier:
            data["code_verifier"] = self.authorize_params.code_verifier

        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        resp = requests.post(str(self.identity_provider.token_url()), data=data, headers=headers)
        resp.raise_for_status()
        token_data = resp.json()
        if "expires_at" not in token_data:
            has_expires_in = "expires_in" in token_data
            has_issued_at = "issued_at" in token_data

            if has_expires_in ^ has_issued_at:
                if not has_expires_in:
                    token_data["expires_in"] = 1500
                if not has_issued_at:
                    token_data["issued_at"] = dt.now(datetime.timezone.utc).isoformat()
        return token_data