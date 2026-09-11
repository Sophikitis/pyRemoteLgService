from unittest.mock import patch

from lg_remote.__main__ import build_app, parse_args
from lg_remote.config import Config


def test_parse_args_defaults_to_no_setup():
    args = parse_args([])
    assert args.setup is False


def test_parse_args_recognizes_setup_flag():
    args = parse_args(["--setup"])
    assert args.setup is True


def test_build_app_loads_existing_config():
    with patch("lg_remote.__main__.Config.load", return_value=Config(tv_ip="192.168.1.50")):
        app = build_app(force_setup=False)
    assert app.config == Config(tv_ip="192.168.1.50")
    assert app.force_setup is False


def test_build_app_passes_through_force_setup():
    with patch("lg_remote.__main__.Config.load", return_value=Config(tv_ip="192.168.1.50")):
        app = build_app(force_setup=True)
    assert app.force_setup is True


def test_build_app_falls_back_to_none_on_config_error():
    from lg_remote.config import ConfigError

    with patch("lg_remote.__main__.Config.load", side_effect=ConfigError("bad file")):
        app = build_app(force_setup=False)
    assert app.config is None
