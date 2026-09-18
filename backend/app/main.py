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


from fastapi.responses import HTMLResponse

# Create the app
app = FastAPI(
    title=settings.app_name,
    description="AI-powered GST compliance agent for India's MSME traders",
    version=settings.app_version,
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
)

@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
      <title>Munim.ai — API Reference & Swagger UI</title>
      <meta charset="utf-8"/>
      <meta name="viewport" content="width=device-width, initial-scale=1">
      <link rel="preconnect" href="https://fonts.googleapis.com">
      <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
      <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
      <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css" />
      <style>
        :root {
          --munim-green: #10b981;
          --munim-dark: #0f172a;
          --munim-bg: #f8fafc;
          --munim-border: #e2e8f0;
        }
        body {
          margin: 0;
          padding: 0;
          background-color: var(--munim-bg) !important;
          font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
          color: var(--munim-dark);
        }
        .munim-topbar {
          background: #ffffff;
          border-bottom: 1px solid var(--munim-border);
          height: 65px;
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 0 32px;
          position: sticky;
          top: 0;
          z-index: 1000;
          box-shadow: 0 1px 2px rgba(0,0,0,0.03);
        }
        .munim-topbar-brand {
          display: flex;
          align-items: center;
          gap: 12px;
          text-decoration: none;
          color: var(--munim-dark);
        }
        .munim-topbar-brand span.logo-title {
          font-weight: 800;
          font-size: 20px;
          letter-spacing: -0.5px;
        }
        .munim-topbar-brand span.logo-badge {
          background: #ecfdf5;
          color: #047857;
          border: 1px solid #a7f3d0;
          padding: 2px 10px;
          border-radius: 9999px;
          font-size: 11px;
          font-weight: 700;
          text-transform: uppercase;
          letter-spacing: 0.5px;
        }
        .munim-topbar-links {
          display: flex;
          align-items: center;
          gap: 12px;
        }
        .munim-topbar-links a {
          font-size: 13px;
          font-weight: 600;
          color: #475569;
          text-decoration: none;
          padding: 6px 14px;
          border-radius: 8px;
          transition: all 0.2s;
        }
        .munim-topbar-links a:hover {
          background: #f1f5f9;
          color: #0f172a;
        }
        .munim-topbar-links a.btn-primary {
          background: #10b981;
          color: #ffffff;
          box-shadow: 0 2px 4px rgba(16, 185, 129, 0.2);
        }
        .munim-topbar-links a.btn-primary:hover {
          background: #059669;
        }
        /* Hide Swagger UI default topbar */
        .swagger-ui .topbar {
          display: none !important;
        }
        /* Main container */
        .swagger-ui {
          font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
          max-width: 1200px;
          margin: 0 auto;
          padding: 24px 16px;
        }
        /* Info block styling to match Munim cards */
        .swagger-ui .info {
          background: #ffffff;
          border: 1px solid var(--munim-border);
          border-radius: 16px;
          padding: 28px !important;
          box-shadow: 0 1px 3px rgba(0,0,0,0.04);
          margin-bottom: 24px !important;
        }
        .swagger-ui .info .title {
          font-family: 'Inter', sans-serif !important;
          font-weight: 900 !important;
          color: #0f172a !important;
          font-size: 28px !important;
          letter-spacing: -0.5px;
        }
        .swagger-ui .info p {
          color: #475569 !important;
          font-size: 14px !important;
          line-height: 1.6;
        }
        /* Filter bar */
        .swagger-ui .filter .operation-filter-input {
          border: 1px solid var(--munim-border) !important;
          border-radius: 10px !important;
          padding: 10px 14px !important;
          font-family: 'Inter', sans-serif !important;
          font-size: 14px !important;
          background: #ffffff !important;
        }
        /* Tag section headings */
        .swagger-ui .opblock-tag {
          font-family: 'Inter', sans-serif !important;
          font-size: 18px !important;
          font-weight: 800 !important;
          color: #0f172a !important;
          border-bottom: 1px solid var(--munim-border) !important;
          padding: 12px 0 !important;
          margin-top: 24px !important;
        }
        /* Operation block styling */
        .swagger-ui .opblock {
          border-radius: 12px !important;
          border: 1px solid var(--munim-border) !important;
          box-shadow: 0 1px 2px rgba(0,0,0,0.02) !important;
          margin-bottom: 12px !important;
          background: #ffffff !important;
          overflow: hidden;
          transition: all 0.2s ease;
        }
        .swagger-ui .opblock:hover {
          box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05) !important;
        }
        /* METHOD BADGES - styled like Munim tags */
        .swagger-ui .opblock .opblock-summary-method {
          border-radius: 8px !important;
          font-family: 'Inter', sans-serif !important;
          font-weight: 800 !important;
          font-size: 11px !important;
          padding: 6px 12px !important;
          min-width: 65px;
          text-align: center;
        }
        .swagger-ui .opblock.opblock-post {
          border-color: #a7f3d0 !important;
          background: #f0fdf4 !important;
        }
        .swagger-ui .opblock.opblock-post .opblock-summary-method {
          background: #10b981 !important;
        }
        .swagger-ui .opblock.opblock-get {
          border-color: #bfdbfe !important;
          background: #f8fafc !important;
        }
        .swagger-ui .opblock.opblock-get .opblock-summary-method {
          background: #3b82f6 !important;
        }
        .swagger-ui .opblock.opblock-delete {
          border-color: #fecaca !important;
          background: #fef2f2 !important;
        }
        .swagger-ui .opblock.opblock-delete .opblock-summary-method {
          background: #ef4444 !important;
        }
        .swagger-ui .opblock-summary-path {
          font-family: 'JetBrains Mono', monospace !important;
          font-size: 14px !important;
          font-weight: 600 !important;
          color: #0f172a !important;
        }
        .swagger-ui .opblock-summary-description {
          font-family: 'Inter', sans-serif !important;
          color: #64748b !important;
          font-size: 13px !important;
        }
        /* Buttons */
        .swagger-ui .btn {
          border-radius: 8px !important;
          font-family: 'Inter', sans-serif !important;
          font-weight: 700 !important;
          font-size: 12px !important;
          transition: all 0.2s;
        }
        .swagger-ui .btn.execute {
          background-color: #10b981 !important;
          border-color: #10b981 !important;
          color: #fff !important;
        }
        .swagger-ui .btn.execute:hover {
          background-color: #059669 !important;
        }
        /* Parameters table & responses */
        .swagger-ui table.parameters, .swagger-ui table.responses-table {
          font-family: 'Inter', sans-serif !important;
        }
        .swagger-ui .response-col_status {
          font-family: 'JetBrains Mono', monospace !important;
          font-weight: 700 !important;
        }
      </style>
    </head>
    <body>
      <div class="munim-topbar">
        <a href="http://localhost:3000/dashboard" class="munim-topbar-brand">
          <span class="logo-title">Munim.ai</span>
          <span class="logo-badge">API Reference v1.0</span>
        </a>
        <div class="munim-topbar-links">
          <a href="http://localhost:3000/dashboard">Dashboard</a>
          <a href="http://localhost:3000/dev">Dev Console</a>
          <a href="/openapi.json" target="_blank">OpenAPI JSON</a>
          <a href="http://localhost:3000/dev" class="btn-primary">⚡ System Diagnostics</a>
        </div>
      </div>
      <div id="swagger-ui"></div>
      <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
      <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-standalone-preset.js"></script>
      <script>
        window.onload = function() {
          const ui = SwaggerUIBundle({
            url: "/openapi.json",
            dom_id: '#swagger-ui',
            deepLinking: true,
            presets: [
              SwaggerUIBundle.presets.apis,
              SwaggerUIStandalonePreset
            ],
            plugins: [
              SwaggerUIBundle.plugins.DownloadUrl
            ],
            layout: "BaseLayout",
            defaultModelsExpandDepth: -1,
            docExpansion: "list",
            displayRequestDuration: true,
            filter: true,
            tryItOutEnabled: true
          });
          window.ui = ui;
        };
      </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

# CORS — allow frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.allowed_origins.split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.api.webhook import router as webhook_router
from app.api.dashboard import router as dashboard_router
from app.api.gstr2b import router as gstr2b_router
from app.api.reports import router as reports_router
from app.api.privacy import router as privacy_router
from app.api.admin import router as admin_router
from app.api.email_webhook import router as email_webhook_router
from app.api.auth import router as auth_router
from app.api.communications import router as communications_router

# Mount routers
app.include_router(auth_router)
app.include_router(webhook_router)
app.include_router(email_webhook_router)
app.include_router(dashboard_router)
app.include_router(gstr2b_router)
app.include_router(reports_router)
app.include_router(privacy_router)
app.include_router(admin_router)
app.include_router(communications_router)


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

