from opnsense.exceptions import (
    OPNsenseError,
    AuthenticationError,
    ValidationError,
    ConfigError,
)

def test_opnsense_error_is_exception():
    """OPNsenseError is an Exception"""
    err = OPNsenseError("test error")
    assert isinstance(err, Exception)
    assert str(err) == "test error"

def test_authentication_error_inheritance():
    """AuthenticationError is an OPNsenseError"""
    err = AuthenticationError("invalid key")
    assert isinstance(err, OPNsenseError)
    assert isinstance(err, Exception)

def test_validation_error_inheritance():
    """ValidationError is an OPNsenseError"""
    err = ValidationError("bad input")
    assert isinstance(err, OPNsenseError)

def test_config_error_inheritance():
    """ConfigError is an OPNsenseError"""
    err = ConfigError("missing config")
    assert isinstance(err, OPNsenseError)
