from google_auth_oauthlib.flow import Flow, _WSGIRequestHandler
import webbrowser
from pathlib import Path
import sys, os
import logging
import wsgiref.simple_server

from utils.logger import LoggerMixin
from .redirect_wsgi_app import CustomRedirectWSGIApp

class FlugiAppFlow(Flow, LoggerMixin):
    
    log: logging.Logger 
    
    _DEFAULT_AUTH_PROMPT_MESSAGE = (
        "Please visit this URL to authorize this application: {url}"
    )
    
    def run_local_server(
        self,
        host = "localhost",
        bind_addr = None,
        port = 8080,
        authorization_prompt_message = _DEFAULT_AUTH_PROMPT_MESSAGE,
        open_browser = True,
        redirect_uri_trailing_slash = True,
        timeout_seconds = None,
        token_audience = None,
        browser = None,
        **kwargs
        ):

        redirect_html = self.get_redirect_html()

        wsgi_app = CustomRedirectWSGIApp(redirect_html)
 
        wsgiref.simple_server.WSGIServer.allow_reuse_address = False
        
        local_server = wsgiref.simple_server.make_server(
            bind_addr or host, 
            port, 
            wsgi_app,
            handler_class = _WSGIRequestHandler
        )

        self._local_server = local_server
        
        try:
            
            redirect_uri_format = (
                "http://{}:{}/" if redirect_uri_trailing_slash else "http://{}:{}"
            )
            
            self.redirect_uri = redirect_uri_format.format(
                host, 
                local_server.server_port
            )
            
            auth_url, _ = self.authorization_url(**kwargs)

            if open_browser:
                
                webbrowser.get(browser).open(auth_url, new = 1, autoraise = True)

            if authorization_prompt_message:
                
                self.log.debug(authorization_prompt_message.format(url = auth_url))

            local_server.timeout = timeout_seconds
            local_server.handle_request()

            authorization_response = wsgi_app.last_request_uri.replace("http", "https")
            
            self.fetch_token(
                authorization_response = authorization_response, 
                audience = token_audience
            )
       
        finally:
            
            local_server.server_close()
            
            self._local_server = None
            
        return self.credentials
    
    def get_redirect_html(self) -> str:
        
        if getattr(sys, "frozen", False):
 
            html_path = os.path.join(Path(sys.executable).parent, "_internal/gui/templates/redirect.html")
       
        else:

            html_path = os.path.join(Path(__file__).resolve().parent.parent.parent.parent, "templates/redirect.html")
            
        with open(html_path, encoding = "utf-8") as f:
            
            html = f.read()
            
        return html

    def close_local_server(self):
        
        if hasattr(self, "_local_server") and self._local_server is not None:
            
            try:
                
                self._local_server.server_close()
           
            except Exception:
                pass
           
            self._local_server = None