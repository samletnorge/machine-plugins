# Browser

`browser_support` provides web automation for agents: a `browser` category, a Playwright
backend, an AI-assisted Stagehand-style backend, and a factory that turns browser actions
into agent-callable tools.

## Enable it

```toml
plugins = ["browser_support", "tool_support", "agent_support", "..."]
```

Install the browser engine if you use Playwright:

```bash
pip install playwright
python -m playwright install
```

## The `browser` category

Operations: `navigate` (POST), `screenshot` (POST), `execute` (POST), `list` (GET).

`BaseBrowser` defines the interface:

```python
class BaseBrowser(ABC):
    async def navigate(self, url: str) -> NavigateResult
    async def click(self, selector: str) -> BrowserResult
    async def fill(self, selector: str, value: str) -> BrowserResult
    async def screenshot(self) -> ScreenshotResult
    async def get_text(self, selector: str) -> ElementResult
    async def evaluate(self, js: str) -> BrowserResult
    async def close(self) -> None
```

Result types: `BrowserResult(success, data, error)`, `NavigateResult(url, title)`,
`ScreenshotResult(image_bytes, format)`, `ElementResult(text, tag, selector)`.

## Playwright backend

```python
from browser_support.playwright_browser import PlaywrightBrowser

browser = await PlaywrightBrowser.create(headless=True, browser_type="chromium")
result = await browser.navigate("https://example.com")
print(result.title)

text = await browser.get_text("h1")
shot = await browser.screenshot()

await browser.close()
```

It also works as an async context manager:

```python
async with await PlaywrightBrowser.create() as browser:
    await browser.navigate("https://example.com")
```

## Stagehand-style backend

`StagehandBrowser` accepts natural-language selectors and resolves them (via a resolver
model) before acting — for example, clicking "the sign in button" instead of `#signin`.

```python
from browser_support.stagehand_browser import StagehandBrowser

browser = StagehandBrowser(...)
await browser.click("the sign in button")
```

If a selector looks like natural language rather than CSS/XPath, it is resolved first.

## Browser tools for agents

`create_browser_tools(browser)` returns a list of `BrowserTool` objects, each with `name`,
`description`, and an async `execute(input)`. The names are:

`browser_navigate`, `browser_click`, `browser_fill`, `browser_screenshot`,
`browser_get_text`, `browser_evaluate`.

```python
from browser_support.tools import create_browser_tools

browser = await PlaywrightBrowser.create()
for browser_tool in create_browser_tools(browser):
    machine.register("tool", browser_tool.name, browser_tool)
```

Because `BrowserTool` exposes `execute`, these **are** executable through the generated
`POST /api/tool/{name}/execute` route (unlike bare `ToolDefinition`s). See
[Tools](tools.md).

Then reference them from an agent:

```python
AgentDefinition(
    name="researcher",
    description="Browses the web and answers questions.",
    model_ref="deepseek/deepseek-chat",
    tool_refs=["browser_navigate", "browser_get_text"],
)
```

## HTTP

```
GET  /api/browser
POST /api/browser/{name}/navigate
POST /api/browser/{name}/screenshot
POST /api/browser/{name}/execute
```

> **Note:** `BrowserSupportPlugin` registers the `browser` **category** but not a concrete
> browser instance. Register a `PlaywrightBrowser` (or `StagehandBrowser`) yourself, for
> example in `when_ready`, before resolving it.

## Tips

- Always `close()` a browser; a leaked Chromium process will hold memory.
- Prefer `get_text` + `browser_evaluate` for structured extraction over screenshots when the
  model only needs text.
- Run headless in servers and containers; `headless=False` needs a display.

---

**Read next:** [Workspaces](workspaces.md) · [Tools](tools.md)

**Source:** `community/browser_support/`.
