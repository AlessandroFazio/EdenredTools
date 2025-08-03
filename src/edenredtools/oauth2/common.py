from edenredtools.system.url import UrlEqualityMode


class Oauth2Urls:
    AUTHORIZE_URL_EQ_MODE = UrlEqualityMode(query_params=["client_id", "scope", "redirect_uri", "response_type"])