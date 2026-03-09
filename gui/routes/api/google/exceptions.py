class GmailException(RuntimeError):
    """There was an ambiguous exception that occurred while handling your
    request."""

class ConnectionError(GmailException):
    """A Connection error occurred."""

class AuthenticationError(GmailException):
    """Gmail Authentication failed."""