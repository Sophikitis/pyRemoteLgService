from pathlib import Path

import pytest
from textual.app import App

STYLESHEET_PATH = Path(__file__).parent.parent / "src" / "lg_remote" / "lg_remote.tcss"


class _StyleOnlyApp(App):
    CSS_PATH = STYLESHEET_PATH


@pytest.mark.asyncio
async def test_stylesheet_loads_without_error():
    app = _StyleOnlyApp()
    async with app.run_test():
        pass  # mounting is enough to trigger CSS parsing
