"""
Shared helper for turning internal exceptions into client-safe HTTP errors.

Raw exception text (DB error strings, file paths, library internals) must
never reach the client — see CWE-209 / OWASP API8:2023. This helper logs the
real exception server-side with a correlation ID, and returns an
HTTPException whose `detail` carries only a generic message plus that ID, so
a user-reported issue can still be traced back to the exact log line.
"""

import logging
import uuid

from fastapi import HTTPException


def safe_http_error(
    logger: logging.Logger,
    message: str,
    exc: Exception,
    status_code: int = 500,
) -> HTTPException:
    """
    Log `exc` (with the real detail and traceback) under a short correlation
    ID, and return an HTTPException suitable for raising to the client whose
    `detail` contains only `message` and that ID — never `str(exc)`.

    Usage:
        except Exception as e:
            raise safe_http_error(logger, "Failed to delete invoice", e)
    """
    error_id = str(uuid.uuid4())[:8]
    logger.error(f"[{error_id}] {message}: {exc}", exc_info=True)
    return HTTPException(status_code=status_code, detail=f"{message}. Reference: {error_id}")
