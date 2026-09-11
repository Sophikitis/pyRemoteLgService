import pytest

from lg_remote.config import Config, ConfigError, is_valid_ipv4


@pytest.mark.parametrize(
    "value",
    ["192.168.1.1", "0.0.0.0", "255.255.255.255", "10.0.0.42"],
)
def test_is_valid_ipv4_accepts_valid_addresses(value):
    assert is_valid_ipv4(value) is True


@pytest.mark.parametrize(
    "value",
    ["", "not an ip", "192.168.1", "192.168.1.256", "192.168.1.1.1", "192.168.01.1"],
)
def test_is_valid_ipv4_rejects_invalid_addresses(value):
    assert is_valid_ipv4(value) is False


def test_load_returns_none_when_file_missing(tmp_path):
    assert Config.load(tmp_path / "missing.toml") is None


def test_save_then_load_round_trips(tmp_path):
    path = tmp_path / "config.toml"
    Config(tv_ip="192.168.1.42", client_name="my-client").save(path)

    loaded = Config.load(path)

    assert loaded == Config(tv_ip="192.168.1.42", client_name="my-client")


def test_save_creates_missing_parent_directories(tmp_path):
    path = tmp_path / "nested" / "dir" / "config.toml"
    Config(tv_ip="192.168.1.42").save(path)
    assert path.exists()


def test_load_raises_config_error_on_malformed_toml(tmp_path):
    path = tmp_path / "config.toml"
    path.write_text("not = [valid toml")

    with pytest.raises(ConfigError):
        Config.load(path)


def test_load_raises_config_error_when_tv_ip_missing(tmp_path):
    path = tmp_path / "config.toml"
    path.write_text('client_name = "my-client"\n')

    with pytest.raises(ConfigError):
        Config.load(path)


def test_load_raises_config_error_when_tv_ip_invalid(tmp_path):
    path = tmp_path / "config.toml"
    path.write_text('tv_ip = "not-an-ip"\n')

    with pytest.raises(ConfigError):
        Config.load(path)
