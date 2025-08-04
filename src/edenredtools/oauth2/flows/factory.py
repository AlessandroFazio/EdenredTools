import base64
from pydantic import HttpUrl
from edenredtools.security.crypto import CryptoUtils
from edenredtools.net.url import Url, UrlEqualityMode
from edenredtools.oauth2.flows.authorization import LocalProxyTokenRequestState, Oauth2AuthorizeRequestParams


class Oauth2AuthorizationFlowFactory:
    _AUTHORIZE_URL_EQ_MODE = UrlEqualityMode(
        query_params=["client_id", "scope", "redirect_uri", "response_type"]
    )
    
    @classmethod
    def create_params(cls, authorize_url: Url, state: str) -> Oauth2AuthorizeRequestParams:
        flow_params = {}
        extra = {}
        for name, val in authorize_url.get_params().items():
            if name in Oauth2AuthorizeRequestParams.transients():
                continue
            elif name in Oauth2AuthorizeRequestParams.non_transients():
                flow_params[name] = val[0]
            else:
                extra[name] = val[0]

        return Oauth2AuthorizeRequestParams(**flow_params, extra=extra, state=state)
        
    @classmethod
    def create_authorize_url(cls, url: HttpUrl) -> Url:
        return Url.from_string(
            url=url.encoded_string(), 
            mode=cls._AUTHORIZE_URL_EQ_MODE
        ).without_params(*Oauth2AuthorizeRequestParams.transients())
    
    @classmethod
    def compute_fingerprint(cls, authorize_url: Url, callback_url: Url, secret: str) -> str:
        return CryptoUtils.compute_fingerprint(
                string="|".join((authorize_url.to_string(), callback_url.to_string())),
                secret=secret
            )

    @classmethod
    def create_state(cls, authorize_url: Url, callback_url: Url, secret: str) -> str:
        state = LocalProxyTokenRequestState(
            authorize_url=HttpUrl(authorize_url.to_string()), 
            callback_url=HttpUrl(callback_url.to_string()),
            fingerprint=cls.compute_fingerprint(authorize_url, callback_url, secret)
        )
        raw = state.model_dump_json().encode("utf-8")
        return base64.urlsafe_b64encode(raw).decode("utf-8")
    