import pytest
from scripts.profile_manager import validate_profile_name

def test_validate_profile_name_valid():
    assert validate_profile_name("ubuntu-base") == True
    assert validate_profile_name("db-cluster-high-mem") == True
    assert validate_profile_name("a") == True
    assert validate_profile_name("123") == True
    assert validate_profile_name("a-b-c-1-2-3") == True

def test_validate_profile_name_invalid():
    assert validate_profile_name("ubuntu_base") == False
    assert validate_profile_name("db cluster") == False
    assert validate_profile_name("Ubuntu-base") == False
    assert validate_profile_name("ubuntu-base!") == False
    assert validate_profile_name("") == False
