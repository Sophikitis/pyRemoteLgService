from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import tomlkit
import tomlkit.exceptions

DEFAULT_CLIENT_NAME = "lg-remote-tui"
DEFAULT_CONFIG_PATH = Path.home() / ".config" / "lg-remote" / "config.toml"

_IPV4_PATTERN = re.compile(
    r"^(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}$"
)


def is_valid_ipv4(value: str) -> bool:
    """Return True if value is a syntactically valid IPv4 address."""
    return bool(_IPV4_PATTERN.match(value.strip()))


class ConfigError(Exception):
    """Raised when the config file exists but cannot be used."""


@dataclass
class Config:
    tv_ip: str
    client_name: str = DEFAULT_CLIENT_NAME
    numbers_enabled: bool = True

    @classmethod
    def load(cls, path: Path = DEFAULT_CONFIG_PATH) -> "Config | None":
        """Load the config file, or return None if it doesn't exist yet."""
        if not path.exists():
            return None

        try:
            document = tomlkit.parse(path.read_text())
        except tomlkit.exceptions.ParseError as exc:
            raise ConfigError(f"Fichier de config invalide ({path}) : {exc}") from exc

        try:
            tv_ip = str(document["tv_ip"])
        except KeyError as exc:
            raise ConfigError(
                f"Le fichier de config ({path}) ne contient pas de clé 'tv_ip'."
            ) from exc

        if not is_valid_ipv4(tv_ip):
            raise ConfigError(f"'{tv_ip}' dans {path} n'est pas une IPv4 valide.")

        client_name = str(document.get("client_name", DEFAULT_CLIENT_NAME))
        numbers_enabled = bool(document.get("numbers_enabled", True))
        return cls(tv_ip=tv_ip, client_name=client_name, numbers_enabled=numbers_enabled)

    def save(self, path: Path = DEFAULT_CONFIG_PATH) -> None:
        """Write this config to path, creating parent directories as needed."""
        path.parent.mkdir(parents=True, exist_ok=True)
        document = tomlkit.document()
        document["tv_ip"] = self.tv_ip
        document["client_name"] = self.client_name
        document["numbers_enabled"] = self.numbers_enabled
        path.write_text(tomlkit.dumps(document))
