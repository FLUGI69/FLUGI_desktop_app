import wsgiref.util

class CustomRedirectWSGIApp(object):

    def __init__(self, redirect_html):

        self.last_request_uri = None
        
        self._redirect_html = redirect_html
        
    def __call__(self, environ, start_response):

        start_response("200 OK", [("Content-type", "text/html; charset=utf-8")])
        
        self.last_request_uri = wsgiref.util.request_uri(environ)
            
        return [self._redirect_html.encode("utf-8")] 