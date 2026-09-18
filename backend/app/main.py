"""
Munim.ai — FastAPI Application Entry Point
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config import get_settings
from app.api.webhook import router as webhook_router
from app.api.dashboard import router as dashboard_router
from app.api.gstr2b import router as gstr2b_router
from app.api.reports import router as reports_router
from app.api.privacy import router as privacy_router
from app.api.admin import router as admin_router
from app.services.llm_router import llm_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s — %(name)s — %(levelname)s — %(message)s",
)
logger = logging.getLogger(__name__)

settings = get_settings()

# APScheduler for scheduled jobs
scheduler = AsyncIOScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle."""
    logger.info(f"🚀 Starting {settings.app_name} v{settings.app_version}")
    logger.info(f"   Environment: {settings.environment}")

    # Start scheduler
    _setup_scheduled_jobs()
    scheduler.start()
    logger.info("📅 Scheduler started")

    # Init LLM router
    await llm_router.initialize()
    logger.info("🧠 LLM router initialized")

    yield

    # Shutdown
    scheduler.shutdown()
    logger.info("👋 Shutting down")


def _setup_scheduled_jobs():
    """Configure scheduled background jobs."""
    from app.domain.supplier_monitor import run_daily_supplier_check

    # Daily supplier health check at 09:00 IST
    scheduler.add_job(
        run_daily_supplier_check,
        "cron",
        hour=9,
        minute=0,
        id="daily_supplier_check",
        replace_existing=True,
    )

    # Deadline alerts on 5th, 10th, 18th of each month at 10:00
    scheduler.add_job(
        _send_deadline_alerts,
        "cron",
        day="5,10,18",
        hour=10,
        minute=0,
        id="deadline_alerts",
        replace_existing=True,
    )

    logger.info("Scheduled jobs configured: supplier_check (daily 09:00), deadline_alerts (5th/10th/18th)")


async def _send_deadline_alerts():
    """Send filing deadline alerts to traders with unresolved issues."""
    from datetime import date
    from app.services.supabase_client import get_supabase
    from app.services import whatsapp

    today = date.today()
    db = get_supabase()

    # GSTR-1 due: 11th, GSTR-3B due: 20th
    if today.day <= 11:
        filing_type = "GSTR-1"
        deadline_day = 11
    else:
        filing_type = "GSTR-3B"
        deadline_day = 20

    days_remaining = deadline_day - today.day

    # Get all traders with unresolved issues
    traders = db.table("traders").select("id, whatsapp_number, name").execute()
    if not traders.data:
        return

    for trader in traders.data:
        invoices = db.table("invoices").select(
            "itc_status, itc_amount_blocked, itc_amount_eligible"
        ).eq("trader_id", trader["id"]).in_(
            "itc_status", ["FIXABLE_BLOCKED", "AT_RISK"]
        ).execute()

        if not invoices.data:
            continue

        blocked_amount = sum(
            (inv.get("itc_amount_blocked") or 0) + (inv.get("itc_amount_eligible") or 0)
            for inv in invoices.data
        )

        if blocked_amount > 0:
            msg = (
                f"⏰ Filing Deadline Alert!\n\n"
                f"{filing_type} filing deadline {days_remaining} din mein hai.\n"
                f"Aapke {len(invoices.data)} unresolved issues hain, "
                f"₹{blocked_amount:,.0f} ITC risk mein hai.\n\n"
                f"Yeh issues {deadline_day} tarikh se pehle fix karo, "
                f"nahi toh credit lose ho jayega."
            )
            await whatsapp.send_text_message(trader["whatsapp_number"], msg)

    logger.info(f"Deadline alerts sent for {filing_type}")


# Create the app
app = FastAPI(
    title=settings.app_name,
    description="AI-powered GST compliance agent for India's MSME traders",
    version=settings.app_version,
    lifespan=lifespan,
)

# CORS — allow frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.api.email_webhook import router as email_webhook_router
from app.api.auth import router as auth_router

# Mount routers
app.include_router(auth_router)
app.include_router(webhook_router)
app.include_router(email_webhook_router)
app.include_router(dashboard_router)
app.include_router(gstr2b_router)
app.include_router(reports_router)
app.include_router(privacy_router)
app.include_router(admin_router)


@app.get("/")
async def root():
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "status": "running",
        "description": "The CA in your pocket that doesn't exist — until now.",
    }


@app.get("/health")
async def health():
    return {"status": "healthy"}
