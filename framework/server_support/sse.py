"""SSE streaming utilities."""

from __future__ import annotations
import json
from typing import Any, AsyncGenerator
from starlette.responses import StreamingResponse


async def sse_generator(event_source: AsyncGenerator[dict[str, Any], None]):
    """Convert an async generator of dicts into SSE-formatted text chunks."""
    async for event in event_source:
        data = json.dumps(event)
        yield f"data: {data}\n\n"


def sse_response(
    event_source: AsyncGenerator[dict[str, Any], None],
) -> StreamingResponse:
    """Create an SSE StreamingResponse from an async event source."""
    return StreamingResponse(
        sse_generator(event_source),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
