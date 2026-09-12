import pytest
from textual.app import App
from textual.widgets import Static

from lg_remote.screens.beta import BetaWarningScreen


class _HostApp(App):
    CSS_PATH = "../src/lg_remote/lg_remote.tcss"

    def on_mount(self) -> None:
        self.push_screen(BetaWarningScreen())


@pytest.mark.asyncio
async def test_beta_warning_mentions_beta_and_irreversible_consequences():
    app = _HostApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        text = str(app.screen.query_one(Static).render()).lower()
        assert "bêta" in text
        assert "irréversible" in text


@pytest.mark.asyncio
async def test_acknowledging_dismisses_the_screen():
    app = _HostApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        assert isinstance(app.screen, BetaWarningScreen)
        await pilot.click("#acknowledge")
        await pilot.pause()
        assert not isinstance(app.screen, BetaWarningScreen)
