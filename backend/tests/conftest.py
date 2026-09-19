import os

# app/services/gemini.py builds a GeminiKeyPool at import time and raises if
# no key is configured. Any test that transitively imports it (webhook,
# invoice_agent, gemini itself) fails at collection in an environment with no
# backend/.env -- this repo has no venv/CI env baked in, so that's the normal
# case here. Setting a placeholder before collection starts (conftest.py
# loads before any test module) satisfies the check; nothing in this suite
# calls Gemini for real, it's all mocked.
os.environ.setdefault("GEMINI_API_KEY", "test-key-for-pytest-collection")
