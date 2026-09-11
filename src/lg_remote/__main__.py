from __future__ import annotations

import argparse

from .app import LGRemoteApp
from .config import Config, ConfigError


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="lg-remote", description="Télécommande TUI pour TV LG webOS."
    )
    parser.add_argument(
        "--setup",
        action="store_true",
        help="Relance l'écran de configuration de l'IP de la TV.",
    )
    return parser.parse_args(argv)


def build_app(force_setup: bool = False) -> LGRemoteApp:
    try:
        config = Config.load()
    except ConfigError:
        config = None
    return LGRemoteApp(config=config, force_setup=force_setup)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    app = build_app(force_setup=args.setup)
    app.run()


if __name__ == "__main__":
    main()
