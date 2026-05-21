"""OAuth device authorization flow modal for TUI."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.widgets import Static, Button, Label, LoadingIndicator
from textual.containers import Vertical


class DeviceAuthModal(ModalScreen[bool]):
    """Modal that guides user through OAuth device flow."""

    def __init__(self, url: str, code: str, poll_fn=None) -> None:
        super().__init__()
        self.auth_url = url
        self.user_code = code
        self.poll_fn = poll_fn

    def compose(self) -> ComposeResult:
        with Vertical(id="device-auth-modal"):
            yield Label("Device Authorization Required", classes="modal-title")
            yield Static(f"\n1. Open: {self.auth_url}")
            yield Static(f"2. Enter code: [bold]{self.user_code}[/bold]\n")
            yield LoadingIndicator()
            yield Static("Waiting for authorization...", id="auth-status")
            yield Button("Cancel", id="cancel-auth", variant="error")

    async def on_mount(self) -> None:
        """Start polling for auth completion."""
        if self.poll_fn:
            self.set_interval(2.0, self._poll)

    async def _poll(self) -> None:
        """Poll for authorization."""
        if self.poll_fn:
            result = await self.poll_fn()
            if result:
                self.dismiss(True)

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel-auth":
            self.dismiss(False)
