"""
Munim-AI — Lambda entrypoint for the dashboard/CA-facing API.

A deliberately separate, slimmer FastAPI app from app/main.py (the Cloud
Run one) rather than reusing it directly:

- No APScheduler/lifespan startup. A Lambda container isn't guaranteed to
  stay warm between invocations, so an in-process cron added at startup
  (main.py's daily_supplier_check / deadline_alerts) can't be trusted to
  actually fire on schedule the way it can on an always-running Cloud Run
  instance. Those two jobs get their own EventBridge Scheduler rules
  instead (see aws/lambdas/deadline_alerts and the supplier-health
  equivalent), invoking the underlying functions directly rather than
  through APScheduler.
- The dashboard-facing routers are mounted: auth, dashboard, gstr2b,
  reports, communications, practice. webhook.py/email_webhook.py (WhatsApp/
  email ingestion) already have their own dedicated AWS Lambda
  implementations (meta_webhook, voice_handler) -- mounting them here too
  would pull in Gemini/Groq/WhatsApp-send dependencies this Lambda doesn't
  need and duplicate a capability that's already live elsewhere in the AWS
  build. admin.py/privacy.py/vendor.py are left off this first cut
  deliberately, not by oversight: every call site that reaches them is
  gated behind an explicit action (admin-key entry, vendor-fix-link
  copying), not anything the dashboard fires on page load, so their
  absence doesn't break normal browsing. Add them back here if/when
  they're needed against DynamoDB.

main.py itself is completely untouched -- the existing Cloud Run
deployment keeps running exactly as it does today, unaffected by any of
this.
"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.api.auth import router as auth_router
from app.api.dashboard import router as dashboard_router
from app.api.gstr2b import router as gstr2b_router
from app.api.reports import router as reports_router
from app.api.communications import router as communications_router
from app.api.practice import router as practice_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s — %(name)s — %(levelname)s — %(message)s")
logger = logging.getLogger(__name__)

settings = get_settings()

app = FastAPI(
    title=f"{settings.app_name} (AWS Lambda)",
    description="Dashboard/CA-facing API, DynamoDB-backed, running on AWS Lambda",
    version=settings.app_version,
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.allowed_origins.split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(dashboard_router)
app.include_router(gstr2b_router)
app.include_router(reports_router)
app.include_router(communications_router)
app.include_router(practice_router)


@app.get("/")
async def root():
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "status": "running",
        "backend": settings.data_backend,
    }


@app.get("/health")
async def health():
    return {"status": "healthy", "backend": settings.data_backend}
