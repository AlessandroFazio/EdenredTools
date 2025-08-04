from abc import ABC, abstractmethod
import base64
import os
import threading
from typing import Any
from flask import Flask, Response, render_template, request, jsonify
from pydantic import ValidationError

from edenredtools.oauth2.flows.authorization import LocalProxyTokenRequestState, Oauth2AuthorizationFlow
from edenredtools.oauth2.flows.factory import Oauth2AuthorizationFlowFactory
from edenredtools.oauth2.flows.registry import AuthorizationFlowRegistry
from edenredtools.oauth2.identity_provider import OidcIdentityProvider
from edenredtools.oauth2.proxies.models import Oauth2LocalProxyConfig, LocalProxyTokenRequest
from edenredtools.oauth2.tokens.registry import Oauth2TokenRegistry
from edenredtools.system.registry import SystemRegistry
from edenredtools.net.url import Url


class Oauth2LocalProxy(ABC):
    def __init__(
        self,
        system: SystemRegistry,
        token_registry: Oauth2TokenRegistry,
        flow_registry: AuthorizationFlowRegistry,
        config: Oauth2LocalProxyConfig
    ) -> None:
        self.system = system
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
        app.route("/proxy/token", methods=["POST"])(self.handle_get_token)
        app.route('/<path:path>', methods=["GET"])(self.handle_catch_all)
        return app

    def handle_health_check(self) -> Any:
        return {"status": "ok"}, 200
    
    def handle_catch_all(self, path: str) -> Any:
        return self.handle_oauth2_callback()
            
    def handle_oauth2_callback(self) -> Any:        
        authorize_url = None
        try:
            state_param = request.args.get("state")
            code_param = request.args.get("code")
            
            if not code_param:
                raise ValueError("Missing authorization code")
            
            # 1. Extract and decode `state`
            if not state_param:
                raise ValueError("Missing `state` parameter in the URL.")
            
            state = None
            try:
                decoded = base64.urlsafe_b64decode(state_param).decode("utf-8")
                state = LocalProxyTokenRequestState.model_validate_json(decoded)
            except Exception:
                raise ValueError("Malformed `state` parameter: unable to decode or parse.")

            authorize_url = Oauth2AuthorizationFlowFactory.create_authorize_url(state.authorize_url)
            callback_url = Url.from_string(state.callback_url.encoded_string())
            
            # 2. Validate hostname
            if request.host != callback_url.hostname():
                raise ValueError("Request rejected: unexpected hostname.")

            # 3. Validate path
            if request.path != callback_url.path():
                raise ValueError("Request rejected: unexpected path.")
            
            expected_fingerprint = Oauth2AuthorizationFlowFactory.compute_fingerprint(
                authorize_url=authorize_url,
                callback_url=callback_url,
                secret=self.config.fingerprint_secret
            )
            if state.fingerprint != expected_fingerprint:
                raise RuntimeError("Callback fingerprint mismatch — possible tampering.")

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

        except ValueError as e:
            if authorize_url: self.flow_regitry.mark_error(authorize_url, e)
            return Response(f"Proxy authorization callback failed: {str(e)}", status=400)

        except Exception as e:
            if authorize_url: self.flow_regitry.mark_error(authorize_url, e)
            return Response(f"Proxy authorization callback failed: {str(e)}", status=500)

    def _handle_oauth2_code_callback(self, authorize_url: Url, flow: Oauth2AuthorizationFlow) -> Any:
        code = request.args.get("code")
        state = request.args.get("state")
        token_response = flow.exchange_code(code, state)
        self.token_registry.set(authorize_url, token_response)

    def handle_get_token(self) -> Any:
        token_request = None
        try:
            token_request = LocalProxyTokenRequest(**request.form.to_dict())

        except ValidationError as ve:
            return Response(f"Invalid request: {ve}", status=400)
        
        authorize_url = Oauth2AuthorizationFlowFactory.create_authorize_url(token_request.authorize_url)
        callback_url = Url.from_string(token_request.callback_url.encoded_string())

        token = self.token_registry.read_valid_token(authorize_url)
        if token:
            return jsonify(token)
    
        flow_state = self.flow_regitry.get_or_create(authorize_url)
        if flow_state.is_initiator():
            def run_flow():
                try:
                    if self.config.autoconfigure_system:
                        self._autoconfigure_system(callback_url)
                        
                    state = Oauth2AuthorizationFlowFactory.create_state(
                        authorize_url=authorize_url, 
                        callback_url=callback_url, 
                        secret=self.config.fingerprint_secret
                    )
                    
                    flow = Oauth2AuthorizationFlow(
                        identity_provider=OidcIdentityProvider(authorize_url.base_url()),
                        authorize_params=Oauth2AuthorizationFlowFactory.create_params(authorize_url, state),
                        client_secret=token_request.client_secret,
                        browser=self.system.broswer
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
            return Response(f"Error occurred: {flow_state.get_error()}")
        
        token = self.token_registry.read_valid_token(authorize_url)
        if token:
            return jsonify(token)
        
        return Response(f"authorization flow completed successfully but could not find related token", 500)

    def _autoconfigure_system(self, callback_url: Url) -> None:
        # DNS auto configuration
        try:
            self.system.dns_resolver.add_mapping(("127.0.0.1", callback_url.hostname()))

            # ip forwarding auto configuration
            src_port, dst_port = callback_url.port(), self.config.port
            if src_port != dst_port:
                self.system.networking.configure_ip_forwarding(src_port, dst_port)
        except Exception as e:
            raise SystemError(f"system error occurred: {e}")
            
    def start(self):
        print(f"Listening on http://0.0.0.0:{self.config.port}")
        self.app.run(host="0.0.0.0", port=self.config.port)
