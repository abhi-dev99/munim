"""Regression test for the blocking-Gemini-call-in-async-def bug.

`gemini.transcribe_voice_note` (and several sibling functions) used to call
the synchronous google-genai SDK method `client.models.generate_content`
directly inside an `async def`, with no `await`/`asyncio.to_thread`. Because
FastAPI runs a single event loop, that multi-second synchronous call blocked
every other concurrent coroutine (other traders' webhook requests, rate-limit
checks, etc.) for its full duration.

This test proves the fix has real effect: it patches the SDK call with a mock
that performs a genuine blocking `time.sleep` (NOT `asyncio.sleep` -- the
whole point is that a synchronous call must no longer block the loop), fires
two calls concurrently via `asyncio.gather`, and asserts they complete in
roughly the time of ONE call rather than two serialized calls. If the
`asyncio.to_thread` wrapping in `app/services/gemini.py` were ever removed or
mis-applied, this test would fail by measuring ~2x the single-call duration.
"""

import asyncio
import time
from types import SimpleNamespace
from unittest.mock import patch

from app.services import gemini

CALL_DURATION = 0.2  # seconds; long enough to dominate scheduling overhead


def _blocking_generate_content(*args, **kwargs):
    """Stand-in for the real synchronous google-genai SDK call.

    Uses time.sleep (a genuine OS-level block) rather than asyncio.sleep,
    because asyncio.sleep would yield control back to the loop on its own and
    would not reproduce the bug being tested for.
    """
    time.sleep(CALL_DURATION)
    return SimpleNamespace(text="namaste, yeh transcript hai")


def test_transcribe_voice_note_runs_concurrently_not_serially():
    async def run_two_concurrently():
        start = time.perf_counter()
        results = await asyncio.gather(
            gemini.transcribe_voice_note(b"fake-audio-bytes-1", "audio/ogg"),
            gemini.transcribe_voice_note(b"fake-audio-bytes-2", "audio/ogg"),
        )
        elapsed = time.perf_counter() - start
        return results, elapsed

    with patch.object(
        gemini.client.models, "generate_content", side_effect=_blocking_generate_content
    ):
        results, elapsed = asyncio.run(run_two_concurrently())

    assert results == ["namaste, yeh transcript hai", "namaste, yeh transcript hai"]

    # Two calls, each individually taking CALL_DURATION, must overlap because
    # asyncio.to_thread runs each in its own worker thread. If the blocking
    # SDK call were made synchronously inside the coroutine again (the bug
    # this guards against), the event loop would serialize them and this
    # would take ~2 * CALL_DURATION instead.
    assert elapsed < CALL_DURATION * 1.5, (
        f"expected concurrent execution close to {CALL_DURATION:.2f}s, "
        f"got {elapsed:.3f}s -- the Gemini call may be blocking the event "
        f"loop again (missing asyncio.to_thread)"
    )


def test_embed_text_runs_concurrently_not_serially():
    async def run_two_concurrently():
        start = time.perf_counter()
        results = await asyncio.gather(
            gemini.embed_text("invoice line item one"),
            gemini.embed_text("invoice line item two"),
        )
        elapsed = time.perf_counter() - start
        return results, elapsed

    def _blocking_embed_content(*args, **kwargs):
        time.sleep(CALL_DURATION)
        return SimpleNamespace(embeddings=[SimpleNamespace(values=[0.1, 0.2, 0.3])])

    with patch.object(
        gemini.client.models, "embed_content", side_effect=_blocking_embed_content
    ):
        results, elapsed = asyncio.run(run_two_concurrently())

    assert results == [[0.1, 0.2, 0.3], [0.1, 0.2, 0.3]]
    assert elapsed < CALL_DURATION * 1.5, (
        f"expected concurrent execution close to {CALL_DURATION:.2f}s, "
        f"got {elapsed:.3f}s -- embed_content may be blocking the event "
        f"loop again (missing asyncio.to_thread)"
    )
