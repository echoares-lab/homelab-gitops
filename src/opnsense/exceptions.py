"""OPNsense API client exceptions"""

class OPNsenseError(Exception):
    """Base exception for all OPNsense errors"""
    pass

class AuthenticationError(OPNsenseError):
    """API key/secret is invalid or missing"""
    pass

class APIError(OPNsenseError):
    """OPNsense API returned an error"""
    pass

class BadRequest(APIError):
    """400: Invalid input"""
    pass

class Unauthorized(APIError):
    """401: Bad credentials"""
    pass

class ServerError(APIError):
    """5xx: OPNsense server error"""
    pass

class ValidationError(OPNsenseError):
    """Input validation failed (before API call)"""
    pass

class ConfigError(OPNsenseError):
    """Missing or invalid configuration"""
    pass

class TimeoutError(OPNsenseError):
    """API request timed out"""
    pass
