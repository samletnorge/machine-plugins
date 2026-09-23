"""Tests for BrowserSupportPlugin registration."""

import pytest

from browser_support import BrowserSupportPlugin, PlaywrightBrowser


class MockCtx:
    def __init__(self):
        self.categories = {}
        self.items = []

    def register_category(self, name, **kwargs):
        self.categories[name] = kwargs

    def register(self, category, name, impl):
        self.items.append((category, name, impl))


@pytest.mark.asyncio
async def test_setup_registers_non_empty_browser_category():
    plugin = BrowserSupportPlugin()
    ctx = MockCtx()
    await plugin.setup(ctx)

    assert "browser" in ctx.categories
    assert ctx.categories["browser"]["operations"]
    assert "playwright" in [
        name for cat, name, _ in ctx.items if cat == "browser"
    ]


@pytest.mark.asyncio
async def test_playwright_implementation_resolves():
    plugin = BrowserSupportPlugin()
    ctx = MockCtx()
    await plugin.setup(ctx)

    impls = [impl for cat, name, impl in ctx.items if cat == "browser" and name == "playwright"]
    assert len(impls) == 1
    assert isinstance(impls[0], PlaywrightBrowser)


@pytest.mark.asyncio
async def test_registration_is_lazy_and_does_not_launch_browser():
    plugin = BrowserSupportPlugin()
    ctx = MockCtx()
    await plugin.setup(ctx)

    impl = next(i for c, n, i in ctx.items if c == "browser" and n == "playwright")
    assert impl._browser is None
    assert impl._playwright is None
    assert impl._page is None
    assert impl._context is None


@pytest.mark.asyncio
async def test_create_raises_clear_import_error_without_playwright():
    from browser_support import playwright_browser as pb

    if pb._HAS_PLAYWRIGHT:
        pytest.skip("playwright is installed; ImportError path not exercised")

    with pytest.raises(ImportError, match="playwright is required"):
        await PlaywrightBrowser.create()
