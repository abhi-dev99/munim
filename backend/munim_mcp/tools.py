import json
import logging
from mcp.types import Tool

logger = logging.getLogger(__name__)

# List of tools to export
_TOOLS = [
    Tool(
        name="check_itc_status",
        description="Check the ITC (Input Tax Credit) summary for a trader. Returns bucketed amounts (confirmed, blocked, at_risk, missed).",
        inputSchema={
            "type": "object",
            "properties": {
                "trader_id": {
                    "type": "string",
                    "description": "The UUID of the trader"
                }
            },
            "required": ["trader_id"]
        }
    ),
    Tool(
        name="get_action_queue",
        description="Get the list of prioritized action items (issues) for a trader that require CA attention.",
        inputSchema={
            "type": "object",
            "properties": {
                "trader_id": {
                    "type": "string",
                    "description": "The UUID of the trader"
                }
            },
            "required": ["trader_id"]
        }
    ),
    Tool(
        name="check_supplier_health",
        description="Get health scores and risk flags for all suppliers linked to a trader.",
        inputSchema={
            "type": "object",
            "properties": {
                "trader_id": {
                    "type": "string",
                    "description": "The UUID of the trader"
                }
            },
            "required": ["trader_id"]
        }
    ),
    Tool(
        name="generate_report",
        description="Generate the monthly Munim PDF report for a trader.",
        inputSchema={
            "type": "object",
            "properties": {
                "trader_id": {
                    "type": "string",
                    "description": "The UUID of the trader"
                },
                "month": {
                    "type": "integer",
                    "description": "Month number (1-12)"
                },
                "year": {
                    "type": "integer",
                    "description": "Year (e.g., 2026)"
                }
            },
            "required": ["trader_id"]
        }
    )
]

def get_tools_list() -> list[Tool]:
    return _TOOLS

async def call_tool_handler(name: str, args: dict) -> str:
    """Routes the tool call to the corresponding backend logic and returns a stringified result."""
    trader_id = args.get("trader_id")
    if not trader_id:
        return "Error: trader_id is required"

    if name == "check_itc_status":
        from app.services.supabase_client import get_itc_summary
        buckets = await get_itc_summary(trader_id)
        if buckets:
            return json.dumps({"status": "success", "itc_buckets": buckets}, indent=2)
        return "No data found for trader."

    elif name == "get_action_queue":
        from app.services.supabase_client import get_invoices_for_trader
        invoices = await get_invoices_for_trader(trader_id)
        actions = []
        for inv in invoices:
            status = inv.get("itc_status", "")
            if status in ("FIXABLE_BLOCKED", "AT_RISK", "FRAUD_FLAGGED"):
                blocked = inv.get("itc_amount_blocked") or 0
                eligible = inv.get("itc_amount_eligible") or 0
                actions.append({
                    "issue": inv.get("itc_block_reason", status),
                    "impact_amount_rs": blocked if blocked > 0 else eligible,
                    "fix_action": "Check with CA" if status == "FRAUD_FLAGGED" else "Correct before filing"
                })
        actions.sort(key=lambda a: a["impact_amount_rs"], reverse=True)
        return json.dumps({"action_items": actions, "count": len(actions)}, indent=2)

    elif name == "check_supplier_health":
        from app.services.supabase_client import get_all_suppliers_for_trader, get_active_supplier_flags
        supplier_links = await get_all_suppliers_for_trader(trader_id)
        result = []
        for link in supplier_links:
            sup = link.get("suppliers", {})
            if sup:
                flags = await get_active_supplier_flags(sup["id"])
                result.append({
                    "supplier_name": "SUPPLIER_HIDDEN_FOR_PRIVACY", # MCP privacy promise
                    "health_score": sup.get("health_score", 100),
                    "flags": [f["flag_type"] for f in flags],
                    "total_invoices": link.get("total_invoice_count", 0)
                })
        return json.dumps({"suppliers": result}, indent=2)

    elif name == "generate_report":
        from app.agents.report_agent import generate_munim_report
        import datetime
        now = datetime.date.today()
        month = args.get("month", now.month)
        year = args.get("year", now.year)
        pdf_url = await generate_munim_report(trader_id, month, year)
        if pdf_url:
            return f"Report generated successfully. PDF URL: {pdf_url}"
        return "Failed to generate report."

    else:
        return f"Error: Tool {name} not recognized."
