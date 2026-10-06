import logging

import pytest

from cf_bypasser.core.bypasser import CloakBypasser
from cf_bypasser.utils.security import redact_proxy

SECRET = "pa/ss?w#rd"


def make_bypasser():
    return CloakBypasser(log=True)


@pytest.mark.parametrize("password", ["plain123", "p@ss", "pa:ss", "p!ss$"])
def test_raw_credentials_still_work(password):
    cfg = make_bypasser().parse_proxy(f"http://user-country-us:{password}@gw.example.com:823")
    assert cfg == {"server": "http://gw.example.com:823",
                   "username": "user-country-us", "password": password}


@pytest.mark.parametrize("password", ["p@ss", "pa:ss", "pa/ss", "pa?ss", "pa#ss", "pa%ss"])
def test_percent_encoded_credentials_are_decoded(password):
    from urllib.parse import quote
    cfg = make_bypasser().parse_proxy(
        f"http://{quote('user@corp', safe='')}:{quote(password, safe='')}@gw.example.com:823")
    assert cfg["username"] == "user@corp"
    assert cfg["password"] == password
    assert cfg["server"] == "http://gw.example.com:823"


def test_redact_proxy_hides_only_the_password():
    assert redact_proxy("http://user:p@ss@gw.example.com:823") == "http://user:***@gw.example.com:823"
    assert redact_proxy("socks5://user:pw@h:1080") == "socks5://user:***@h:1080"
    assert redact_proxy("http://gw.example.com:823") == "http://gw.example.com:823"
    assert redact_proxy(None) is None


def test_proxy_without_port_logs_no_password(caplog):
    caplog.set_level(logging.INFO)
    assert make_bypasser().parse_proxy("http://user:topsecret@gw.example.com") is None
    assert "topsecret" not in caplog.text


def test_unparsable_proxy_logs_no_part_of_the_password(caplog):
    caplog.set_level(logging.INFO)
    assert make_bypasser().parse_proxy(f"http://user:{SECRET}@gw.example.com:823") is None
    assert "Error parsing proxy" in caplog.text
    assert "pa" not in caplog.text.split("Error parsing proxy", 1)[1]
