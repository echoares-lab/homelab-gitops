import pytest
from scripts.role_manager import validate_role_name

def test_validate_role_name_valid():
    assert validate_role_name("install_nginx") is True
    assert validate_role_name("my_role_123") is True
    assert validate_role_name("123_role") is True
    assert validate_role_name("a") is True
    assert validate_role_name("1") is True
    assert validate_role_name("_") is True

def test_validate_role_name_invalid():
    assert validate_role_name("") is False
    assert validate_role_name("Install_nginx") is False
    assert validate_role_name("install-nginx") is False
    assert validate_role_name("install nginx") is False
    assert validate_role_name("install@nginx") is False
    assert validate_role_name("install_nginx!") is False
    assert validate_role_name("INSTALL_NGINX") is False
