from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from typing import Any, Callable

from studio_support.context_models import RuntimeAttachment, StudioContext


class AttachmentManager:
    def __init__(
        self,
        *,
        resolver: Callable[[StudioContext], Any],
        initial_attachment: RuntimeAttachment,
    ) -> None:
        self._resolver = resolver
        self._attachment = initial_attachment
        self._machine: Any = None

    def attachment(self) -> RuntimeAttachment:
        return self._attachment

    def get_machine(self) -> Any:
        return self._machine

    def snapshot(self) -> tuple[RuntimeAttachment, Any]:
        return self._attachment, self._machine

    def restore(self, snapshot: tuple[RuntimeAttachment, Any]) -> None:
        self._attachment, self._machine = snapshot

    def attach(self, context: StudioContext) -> RuntimeAttachment:
        self._attachment = replace(
            self._attachment,
            context=context,
            status="attaching",
            machine_name=None,
            attached_at=None,
            error=None,
        )
        try:
            machine = self._resolver(context)
            if hasattr(machine, "list_categories"):
                machine.list_categories()
        except Exception as exc:
            self._machine = None
            self._attachment = replace(
                self._attachment,
                context=context,
                status="failed",
                machine_name=None,
                attached_at=None,
                error=str(exc),
            )
            return self._attachment

        self._machine = machine
        self._attachment = replace(
            self._attachment,
            context=context,
            status="attached",
            machine_name=getattr(machine, "name", None),
            attached_at=datetime.now(UTC).isoformat(),
            error=None,
        )
        return self._attachment
