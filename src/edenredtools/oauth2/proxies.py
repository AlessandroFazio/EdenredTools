from abc import ABC, abstractmethod
import base64
from dataclasses import dataclass
import os
import threading
from flask import Flask, Response, json, render_template, request, jsonify

from edenredtools.oauth2.common import Oauth2Urls
from edenredtools.oauth2.flows.authorization import Oauth2AuthorizationFlow, Oauth2AuthorizeRequestParams
from edenredtools.oauth2.flows.registry import AuthorizationFlowRegistry
from edenredtools.oauth2.identity_provider import OidcIdentityProvider
from edenredtools.oauth2.tokens.registry import Oauth2TokenRegistry
from edenredtools.system.url import Url


@dataclass
class Oauth2LocalProxyConfig:
    hostname: str
    port: int
    callback_path: str
    authorize_flow_timeout: int
    
    
class Oauth2LocalProxy(ABC):
    def __init__(
        self,
        token_registry: Oauth2TokenRegistry,
        flow_registry: AuthorizationFlowRegistry,
        config: Oauth2LocalProxyConfig
    ) -> None:
        self.token_registry = token_registry
        self.flow_regitry = flow_registry
        self.config = config

    @abstractmethod
    def handle_health_check(self) -> None: ...

    @abstractmethod
    def handle_oauth2_callback(self) -> None: ...

    @abstractmethod
    def handle_get_token(self) -> None: ...


class FlaskOauth2LocalProxy(Oauth2LocalProxy):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.app = self._configure_flask()
        
    def _configure_flask(self) -> Flask:
        app = Flask(__name__, template_folder=os.path.join(os.path.dirname(__file__), 'templates'))
        app.route("/proxy/health", methods=["GET"])(self.handle_health_check)
        app.route(self.config.callback_path, methods=["GET"])(self.handle_oauth2_callback)
        app.route("/proxy/token", methods=["GET"])(self.handle_get_token)
        return app

    def handle_health_check(self):
        return {"status": "ok"}, 200
    
    def handle_oauth2_callback(self) -> None:
        authorize_url = None
        try:
            # 1. Validate hostname
            if request.host != self.config.hostname:
                raise ValueError("Request rejected: unexpected hostname.")

            # 2. Extract and decode `state`
            state_param = request.args.get("state")
            if not state_param:
                raise ValueError("Missing `state` parameter in the URL.")

            state = None
            try:
                decoded = base64.urlsafe_b64decode(state_param).decode("utf-8")
                state = json.loads(decoded)
            except Exception:
                raise ValueError("Malformed `state` parameter: unable to decode or parse.")

            # 3. Validate and parse `authorize_url` from state
            if not isinstance(state, dict) or "authorize_url" not in state:
                raise ValueError("`state` parameter is missing `authorize_url`.")

            authorize_url = Url.from_string(state["authorize_url"], mode=Oauth2Urls.AUTHORIZE_URL_EQ_MODE)

            # 4. Retrieve flow
            flow_state = self.flow_regitry.get(authorize_url)
            if not flow_state:
                raise ValueError("Authorization flow not found for given state.")

            flow = flow_state.get_flow()
            if not flow:
                raise RuntimeError("Flow object is missing in flow state.")

            # 5. Dispatch by response type
            if flow.authorize_params.response_type == "code":
                self._handle_oauth2_code_callback(authorize_url, flow)
                self.flow_regitry.mark_done(authorize_url)
                return render_template("redirect_callback.html")
            else:
                raise ValueError(f"Unsupported response_type: {flow.authorize_params.response_type}")

        except Exception as e:
            if authorize_url:
                self.flow_regitry.mark_error(authorize_url, str(e))
            return Response(f"Proxy authorization callback failed: {str(e)}", status=400)

    def _handle_oauth2_code_callback(self, authorize_url: Url, flow: Oauth2AuthorizationFlow) -> None:
        code = request.args.get("code")
        state = request.args.get("state")
        if not code:
            return "Missing authorization code", 400

        token_response = flow.exchange_code(code, state)
        self.token_registry.set(authorize_url, token_response)

    def handle_get_token(self):
        authorize_url = request.args.get("authorize_url")
        if not authorize_url:
            return "Missing authorize_url", 400
        
        client_secret = request.args.get("client_secret")
        
        authorize_url = Url.from_string(authorize_url, mode=Oauth2Urls.AUTHORIZE_URL_EQ_MODE)\
            .without_params(*Oauth2AuthorizeRequestParams.transients())

        token = self.token_registry.read_valid_token(authorize_url)
        if token:
            return jsonify(token)
    
        flow_state = self.flow_regitry.get_or_create(authorize_url)
        if flow_state.is_initiator():
            def run_flow():
                try:
                    flow = Oauth2AuthorizationFlow(
                        identity_provider=OidcIdentityProvider(authorize_url.get_base()),
                        authorize_params=Oauth2AuthorizeRequestParams.from_authorize_url(authorize_url),
                        client_secret=client_secret
                    )   
                    flow_state.set_flow(flow)
                    flow.commence()
                except Exception as e:
                    self.flow_regitry.mark_error(authorize_url, e)

            threading.Thread(target=run_flow, daemon=True).start()
                
        try:
            flow_state.wait_for_flow(timeout=self.config.authorize_flow_timeout)

        except TimeoutError as e:
            self.flow_regitry.mark_error(authorize_url, e)
            return Response(f"Error occurred: {e}")
        
        if flow_state.in_error():
            return Response(f"Error occurred: {e}")
        
        token = self.token_registry.read_valid_token(authorize_url)
        if token:
            return jsonify(token)
        
        return Response(f"authorization flow completed successfully but could not find related token", 500)

    def start(self):
        print(f"Listening on http://0.0.0.0:{self.config.port}")
        print(f"Token endpoint: /proxy/token")
        print(f"Callback endpoint: {self.config.callback_path}")
        self.app.run(host="0.0.0.0", port=self.config.port)
