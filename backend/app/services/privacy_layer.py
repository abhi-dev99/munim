import hashlib
import json
import logging
import uuid
from datetime import datetime
from typing import Callable, Tuple, Dict, Any, List
import os

logger = logging.getLogger(__name__)

AUDIT_LOG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "logs", "privacy_audit.jsonl")

# Ensure logs dir exists
os.makedirs(os.path.dirname(AUDIT_LOG_PATH), exist_ok=True)

class PrivacyLayer:
    def __init__(self):
        self._session_map: Dict[str, Dict[str, Any]] = {}
        
    def _bucket_amount(self, amount: float) -> str:
        try:
            val = float(amount)
            if val <= 10000: return "SMALL"
            if val <= 50000: return "MEDIUM"
            if val <= 100000: return "HIGH"
            if val <= 500000: return "VERY_HIGH"
            return "LARGE"
        except (ValueError, TypeError):
            return "UNKNOWN"

    def _hash_gstin(self, gstin: str) -> str:
        if not gstin: return ""
        hash_val = hashlib.sha256(gstin.encode()).hexdigest()[:4]
        return f"SUP_{hash_val}"

    def anonymize_for_llm(self, context: dict, llm_target: str, task: str) -> Tuple[Dict[str, Any], Callable[[Dict[str, Any]], Dict[str, Any]]]:
        """
        """
        if task in ("DIAGNOSIS", "SUMMARY"):
            return context, lambda x: x

        session_id = str(uuid.uuid4())
        anonymized_context = {}
        real_data = {}
        fields_anonymized = []
        fields_sent_raw = []

        # Simple sequential ID for suppliers in this session
        supplier_counter = 1
        supplier_map = {}

        for k, v in context.items():
            if k == "gstin" or k.endswith("gstin_supplier"):
                anon_val = self._hash_gstin(str(v))
                anonymized_context[k] = anon_val
                real_data[anon_val] = v
                fields_anonymized.append(k)
            elif k in ("total_amount", "itc_amount_eligible", "itc_amount_blocked", "amount"):
                anon_val = self._bucket_amount(v)
                anonymized_context[k] = anon_val
                fields_anonymized.append(k)
            elif k in ("supplier_name", "trader_name", "business_name"):
                if str(v) not in supplier_map:
                    supplier_map[str(v)] = f"PARTY_{supplier_counter}"
                    supplier_counter += 1
                anon_val = supplier_map[str(v)]
                anonymized_context[k] = anon_val
                real_data[anon_val] = v
                fields_anonymized.append(k)
            elif k in ("invoice_number", "id", "trader_id", "invoice_id"):
                anon_val = str(v)[-4:] if v else "UKNW"
                anonymized_context[k] = anon_val
                fields_anonymized.append(k)
            elif k in ("phone", "whatsapp_number", "ca_whatsapp_number", "pan"):
                anonymized_context[k] = "[REDACTED]"
                fields_anonymized.append(k)
            else:
                # pass through (e.g., status, hsn_code, month, year)
                anonymized_context[k] = v
                fields_sent_raw.append(k)

        self._session_map[session_id] = real_data

        # Write audit log
        audit_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "event": "anonymize_for_llm",
            "llm_target": llm_target,
            "task": task,
            "fields_anonymized": fields_anonymized,
            "fields_sent_raw": fields_sent_raw,
            "session_id": session_id
        }
        
        try:
            with open(AUDIT_LOG_PATH, "a", encoding="utf-8") as f:
                f.write(json.dumps(audit_entry) + "\n")
        except Exception as e:
            logger.error(f"Failed to write privacy audit log: {e}")

        # The file above is the local-development copy and nothing more. On
        # App Runner the filesystem is per-instance and ephemeral, so it is wiped
        # on every deploy, cold start and scale event, and two instances hold
        # different halves of the trail — which makes "every model call is
        # logged and the trail is readable by the CA" untrue in production
        # exactly where it is being claimed. The durable copy is the audit_log
        # table. Best-effort: an audit write must never break the model call it
        # is describing, but a silent failure would recreate the same problem,
        # so failures are logged loudly.
        self._persist_audit_entry(context.get("trader_id"), audit_entry)

        def de_anonymize(response_data: Dict[str, Any]) -> Dict[str, Any]:
            """Re-attaches real data if anonymized tokens are found in the response."""
            sess_data = self._session_map.get(session_id, {})
            restored = {}
            for k, v in response_data.items():
                if isinstance(v, str) and v in sess_data:
                    restored[k] = sess_data[v]
                else:
                    restored[k] = v
            # Clean up session
            self._session_map.pop(session_id, None)
            return restored

        return anonymized_context, de_anonymize

    def _persist_audit_entry(self, trader_id: Any, entry: Dict[str, Any]) -> None:
        """
        Write one anonymisation record to the audit_log table.

        trader_id is whatever the calling context carried; it is a real FK to
        traders(id), so anything that is not a UUID is stored as null rather
        than failing the insert. A null-owner row still records that the call
        happened — it just cannot be attributed to one client in the CA's view.
        """
        try:
            from app.services.supabase_client import get_supabase

            owner = str(trader_id) if trader_id else None
            if owner:
                try:
                    uuid.UUID(owner)
                except (ValueError, AttributeError, TypeError):
                    owner = None

            get_supabase().table("audit_log").insert({
                "trader_id": owner,
                "event_type": "llm_anonymization",
                "event_data": entry,
            }).execute()
        except Exception as e:
            logger.error(f"Failed to persist privacy audit entry to audit_log: {e}")

    def clear_session(self, session_id: str):
        self._session_map.pop(session_id, None)

privacy_layer = PrivacyLayer()
