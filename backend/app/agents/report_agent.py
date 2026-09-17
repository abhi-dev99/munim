"""
Munim.ai — Report Generation Agent
Generates the monthly Munim Report PDF for traders and their CAs.
"""

import logging
from datetime import date
from typing import Optional

from jinja2 import Template
from weasyprint import HTML

from app.services.supabase_client import (
    get_supabase,
    get_invoices_for_trader,
    get_itc_summary,
    get_all_suppliers_for_trader,
    get_active_supplier_flags,
    upload_file,
)
from app.services import whatsapp

logger = logging.getLogger(__name__)

# Munim Report HTML template
REPORT_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');

    * { margin: 0; padding: 0; box-sizing: border-box; }
    body {
        font-family: 'Inter', sans-serif;
        color: #1a1a2e;
        padding: 40px;
        font-size: 11px;
        line-height: 1.5;
    }

    .header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-bottom: 3px solid #0f3460;
        padding-bottom: 20px;
        margin-bottom: 30px;
    }
    .header h1 {
        font-size: 28px;
        color: #0f3460;
        font-weight: 700;
    }
    .header .meta {
        text-align: right;
        color: #666;
    }

    .section {
        margin-bottom: 25px;
    }
    .section h2 {
        font-size: 16px;
        color: #0f3460;
        border-bottom: 1px solid #e0e0e0;
        padding-bottom: 5px;
        margin-bottom: 10px;
    }

    .summary-grid {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 15px;
        margin-bottom: 20px;
    }
    .summary-card {
        padding: 15px;
        border-radius: 8px;
        text-align: center;
    }
    .card-confirmed { background: #e8f5e9; border: 1px solid #4caf50; }
    .card-blocked { background: #fff3e0; border: 1px solid #ff9800; }
    .card-risk { background: #fce4ec; border: 1px solid #f44336; }
    .card-missed { background: #e3f2fd; border: 1px solid #2196f3; }
    .card-ineligible { background: #f5f5f5; border: 1px solid #9e9e9e; }

    .summary-card .amount {
        font-size: 22px;
        font-weight: 700;
        margin-top: 5px;
    }
    .summary-card .label {
        font-size: 10px;
        color: #666;
        text-transform: uppercase;
    }

    table {
        width: 100%;
        border-collapse: collapse;
        margin-top: 10px;
    }
    th, td {
        padding: 6px 8px;
        text-align: left;
        border-bottom: 1px solid #eee;
        font-size: 10px;
    }
    th {
        background: #f5f5f5;
        font-weight: 600;
        color: #333;
    }
    tr:nth-child(even) { background: #fafafa; }

    .status-confirmed { color: #4caf50; font-weight: 600; }
    .status-blocked { color: #ff9800; font-weight: 600; }
    .status-risk { color: #f44336; font-weight: 600; }
    .status-fraud { color: #9c27b0; font-weight: 600; }

    .health-good { color: #4caf50; }
    .health-warn { color: #ff9800; }
    .health-bad { color: #f44336; }

    .footer {
        margin-top: 30px;
        padding-top: 15px;
        border-top: 1px solid #e0e0e0;
        text-align: center;
        color: #999;
        font-size: 9px;
    }

    .action-item {
        padding: 8px 12px;
        margin-bottom: 6px;
        border-left: 3px solid #ff9800;
        background: #fff3e0;
        border-radius: 0 4px 4px 0;
    }
    .action-item .impact {
        font-weight: 700;
        color: #f44336;
    }
</style>
</head>
<body>

<div class="header">
    <div>
        <h1>📋 Munim Report</h1>
        <p><strong>{{ trader_name }}</strong> — {{ business_name }}</p>
    </div>
    <div class="meta">
        <p><strong>{{ month_label }} {{ year }}</strong></p>
        <p>Generated: {{ generated_date }}</p>
        <p>GSTIN: {{ trader_gstin }}</p>
    </div>
</div>

<!-- Section 1: Executive Summary -->
<div class="section">
    <h2>1. Executive Summary</h2>
    <div class="summary-grid">
        <div class="summary-card card-confirmed">
            <div class="label">Confirmed ITC</div>
            <div class="amount">₹{{ confirmed }}</div>
        </div>
        <div class="summary-card card-blocked">
            <div class="label">Blocked (Fixable)</div>
            <div class="amount">₹{{ blocked }}</div>
        </div>
        <div class="summary-card card-risk">
            <div class="label">At-Risk</div>
            <div class="amount">₹{{ at_risk }}</div>
        </div>
    </div>
    <p><strong>Total Invoices Processed:</strong> {{ total_invoices }} | <strong>Recovery Possible:</strong> ₹{{ total_recovery }}</p>
</div>

<!-- Section 2: Issues Requiring CA Action -->
<div class="section">
    <h2>2. Issues Requiring CA Action (₹ Impact)</h2>
    {% if issues %}
    {% for issue in issues %}
    <div class="action-item">
        <strong>{{ issue.supplier }}</strong> — {{ issue.reason }}
        <span class="impact"> | ₹{{ issue.amount }}</span>
        <br><em>Fix: {{ issue.fix_action }}</em>
    </div>
    {% endfor %}
    {% else %}
    <p>✅ No issues this month!</p>
    {% endif %}
</div>

<!-- Section 3: Invoice Summary -->
<div class="section">
    <h2>3. All Processed Invoices</h2>
    <table>
        <tr>
            <th>Date</th>
            <th>Supplier</th>
            <th>Amount</th>
            <th>ITC</th>
            <th>Status</th>
        </tr>
        {% for inv in invoices[:30] %}
        <tr>
            <td>{{ inv.date }}</td>
            <td>{{ inv.supplier }}</td>
            <td>₹{{ inv.amount }}</td>
            <td>₹{{ inv.itc }}</td>
            <td class="status-{{ inv.status_class }}">{{ inv.status }}</td>
        </tr>
        {% endfor %}
        {% if invoices|length > 30 %}
        <tr><td colspan="5"><em>... and {{ invoices|length - 30 }} more</em></td></tr>
        {% endif %}
    </table>
</div>

<!-- Section 4: Supplier Health -->
<div class="section">
    <h2>4. Supplier Health Report</h2>
    <table>
        <tr>
            <th>Supplier</th>
            <th>GSTIN</th>
            <th>Health Score</th>
            <th>Flags</th>
            <th>Invoices</th>
        </tr>
        {% for s in suppliers %}
        <tr>
            <td>{{ s.name }}</td>
            <td>{{ s.gstin }}</td>
            <td class="health-{{ s.health_class }}">{{ s.health_score }}/100</td>
            <td>{{ s.flags }}</td>
            <td>{{ s.invoice_count }}</td>
        </tr>
        {% endfor %}
    </table>
</div>

<div class="footer">
    <p>Generated by Munim.ai — Your GST Compliance Agent</p>
    <p>This report is auto-generated. Please verify with your CA before filing.</p>
</div>

</body>
</html>
"""


async def generate_munim_report(
    trader_id: str,
    month: Optional[int] = None,
    year: Optional[int] = None,
) -> Optional[str]:
    """
    Generate the monthly Munim Report PDF and upload to Supabase Storage.
    Returns the public URL of the generated PDF.
    """
    now = date.today()
    month = month or now.month
    year = year or now.year

    db = get_supabase()

    # Fetch trader info
    trader = db.table("traders").select("*").eq("id", trader_id).execute()
    if not trader.data:
        logger.error(f"Trader {trader_id} not found")
        return None
    trader_data = trader.data[0]

    # Fetch ITC summary
    buckets = await get_itc_summary(trader_id)

    # Fetch invoices
    invoices = await get_invoices_for_trader(trader_id, month, year)

    # Fetch suppliers
    supplier_links = await get_all_suppliers_for_trader(trader_id)

    # Build template data
    confirmed = buckets.get("confirmed", 0)
    blocked = buckets.get("fixable_blocked", 0)
    at_risk = buckets.get("at_risk", 0)
    missed = buckets.get("missed", 0)
    total_recovery = blocked + at_risk + missed

    # Issues requiring CA action
    issues = []
    for inv in invoices:
        status = inv.get("itc_status", "")
        if status in ("FIXABLE_BLOCKED", "AT_RISK", "FRAUD_FLAGGED"):
            blocked_amt = inv.get("itc_amount_blocked") or inv.get("itc_amount_eligible") or 0
            issues.append({
                "supplier": inv.get("gstin_supplier", "Unknown"),
                "reason": inv.get("itc_block_reason", status),
                "amount": f"{blocked_amt:,.0f}",
                "fix_action": _get_fix_action(status),
            })

    issues.sort(key=lambda x: float(x["amount"].replace(",", "")), reverse=True)

    # Format invoices for table
    invoice_rows = []
    status_class_map = {
        "CONFIRMED": "confirmed", "FIXABLE_BLOCKED": "blocked",
        "AT_RISK": "risk", "FRAUD_FLAGGED": "fraud",
    }
    for inv in invoices:
        itc_status = inv.get("itc_status", "")
        itc_amt = inv.get("itc_amount_eligible") or inv.get("itc_amount_blocked") or 0
        invoice_rows.append({
            "date": inv.get("invoice_date", ""),
            "supplier": inv.get("supplier_name") or inv.get("gstin_supplier", "Unknown"),
            "amount": f"{inv.get('total_amount', 0):,.0f}",
            "itc": f"{itc_amt:,.0f}",
            "status": itc_status,
            "status_class": status_class_map.get(itc_status, "confirmed"),
        })

    # Format suppliers
    supplier_rows = []
    for link in supplier_links:
        supplier = link.get("suppliers", {})
        if not supplier:
            continue
        flags = await get_active_supplier_flags(supplier["id"])
        health = supplier.get("health_score", 100)
        health_class = "good" if health >= 70 else ("warn" if health >= 40 else "bad")
        supplier_rows.append({
            "name": supplier.get("legal_name", "Unknown"),
            "gstin": supplier.get("gstin", ""),
            "health_score": health,
            "health_class": health_class,
            "flags": ", ".join(f["flag_type"] for f in flags) if flags else "None",
            "invoice_count": link.get("total_invoice_count", 0),
        })

    supplier_rows.sort(key=lambda s: s["health_score"])

    # Render HTML
    month_names = [
        "", "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December",
    ]
    template = Template(REPORT_TEMPLATE)
    html_content = template.render(
        trader_name=trader_data.get("name", "Trader"),
        business_name=trader_data.get("business_name", ""),
        trader_gstin=trader_data.get("gstin", ""),
        month_label=month_names[month],
        year=year,
        generated_date=now.isoformat(),
        confirmed=f"{confirmed:,.0f}",
        blocked=f"{blocked:,.0f}",
        at_risk=f"{at_risk:,.0f}",
        total_invoices=len(invoices),
        total_recovery=f"{total_recovery:,.0f}",
        issues=issues,
        invoices=invoice_rows,
        suppliers=supplier_rows,
    )

    # Generate PDF
    try:
        pdf_bytes = HTML(string=html_content).write_pdf()
    except Exception as e:
        logger.error(f"PDF generation failed: {e}")
        return None

    # Upload to Supabase Storage
    filename = f"munim_report_{trader_id}_{year}_{month:02d}.pdf"
    pdf_url = await upload_file("reports", filename, pdf_bytes, "application/pdf")

    # Store report metadata
    try:
        db.table("munim_reports").upsert({
            "trader_id": trader_id,
            "month": month,
            "year": year,
            "pdf_url": pdf_url,
            "total_invoices_processed": len(invoices),
            "total_itc_confirmed": confirmed,
            "total_itc_blocked": blocked,
            "total_itc_at_risk": at_risk,
            "total_itc_missed": missed,
            "total_issues_count": len(issues),
        }, on_conflict="trader_id,month,year").execute()
    except Exception as e:
        logger.error(f"Failed to store report metadata: {e}")

    logger.info(f"Munim Report generated for trader {trader_id} — {month_names[month]} {year}")
    return pdf_url


async def send_report_to_trader(trader_id: str, pdf_url: str):
    """Send the Munim Report PDF to trader and CA via WhatsApp."""
    db = get_supabase()
    trader = db.table("traders").select("*").eq("id", trader_id).execute()
    if not trader.data:
        return

    trader_data = trader.data[0]
    phone = trader_data["whatsapp_number"]

    # Send to trader
    await whatsapp.send_text_message(
        phone,
        "📋 Aapka monthly Munim Report tayyar hai!\n\n"
        "Isme hai: ITC summary, issues, supplier health, aur CA ke liye filing data.\n"
        "PDF neeche hai 👇"
    )
    await whatsapp.send_document(phone, pdf_url, "Munim Report", "munim_report.pdf")

    # Send to CA if registered
    ca_phone = trader_data.get("ca_whatsapp_number")
    if ca_phone:
        await whatsapp.send_text_message(
            ca_phone,
            f"📋 Munim Report — {trader_data.get('business_name', 'Client')}\n\n"
            f"Monthly compliance report ready for review."
        )
        await whatsapp.send_document(ca_phone, pdf_url, "Munim Report", "munim_report.pdf")


def _get_fix_action(status: str) -> str:
    actions = {
        "FIXABLE_BLOCKED": "Correct HSN code/rate before filing",
        "AT_RISK": "Confirm supplier has filed GSTR-1",
        "FRAUD_FLAGGED": "Verify invoice authenticity before claiming",
    }
    return actions.get(status, "Consult CA")
