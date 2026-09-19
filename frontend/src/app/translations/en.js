// English (default) — this file is the canonical key set. Every other
// language file (hi/mr/gu) must define exactly these keys; LanguageContext's
// t() falls back to this file when a key is missing elsewhere and warns in
// development when it is missing from here too.
const en = {
  // Navigation
  nav_money_meter: "Money Meter",
  nav_supplier_trust: "Supplier Trust",
  nav_action_queue: "Action Queue",
  nav_monthly_reports: "Monthly Reports",
  nav_my_profile: "My Profile",
  nav_sign_out: "Sign Out",
  nav_whatsapp_alerts: "WhatsApp Alerts",
  nav_send_test_alert: "Send Test Alert",
  nav_sending: "Sending…",

  // Dashboard header
  hdr_composition: "Composition",
  hdr_live: "Live",
  hdr_switch_trader: "Switch Trader",
  hdr_no_traders: "No traders found",

  // Money Meter cards
  mm_confirmed_itc: "Confirmed ITC",
  mm_at_risk: "At Risk / Blocked",
  mm_potential_recovery: "Potential Recovery",
  mm_this_month_live: "This month · live",
  mm_requires_action: "Requires action by 18th →",
  mm_fix_supplier: "Fix supplier issues to unlock",
  mm_invoices_scanned: "Invoices Scanned",
  mm_suppliers_tracked: "Suppliers Tracked",
  mm_open_issues: "Open Issues",

  // Composition mode
  mm_total_sales: "Total Sales",
  mm_est_tax: "Est. Tax (1%)",
  mm_cmp08: "CMP-08 Status",
  mm_overdue: "OVERDUE",
  mm_due_soon: "DUE SOON",
  mm_due_by_18th: "Due by 18th",
  mm_quarter_to_date: "Quarter-to-date",

  // Invoice feed
  inv_records: "Invoice Records",
  inv_live_sync: "Live Sync",
  inv_search: "Search Supplier, GSTIN, Invoice…",
  inv_all_status: "All Status",
  inv_confirmed: "✓ Confirmed",
  inv_blocked: "⚠ Blocked",
  inv_at_risk: "↯ At Risk",
  inv_fraud: "✕ Fraud",
  inv_duplicate: "⧉ Duplicate",
  inv_resolved: "✓ Resolved",
  inv_ineligible: "— Ineligible",
  inv_no_records: "No records found.",

  // Supplier Trust
  sup_risk_title: "Supplier Risk",
  sup_good_short: "Good",
  sup_at_risk_short: "At Risk",
  sup_blocked_short: "Blocked",
  sup_needs_attention: "Needs Attention",
  sup_no_data_short: "No supplier data yet.",
  sup_good_standing: "Good Standing",
  sup_at_risk: "At Risk",
  sup_blocked: "Blocked",
  sup_search: "Search supplier or GSTIN…",
  sup_all_status: "All Status",
  sup_supplier: "Supplier",
  sup_gstin: "GSTIN",
  sup_health: "Health",
  sup_status: "Status",
  act_days_left: "{count} days left to chase supplier",
  act_due_today: "Last day to chase supplier",
  act_window_closed: "Chase window closed",
  sup_itc: "ITC",
  sup_issues: "Issues",
  sup_action: "Action",
  sup_view: "View",
  sup_fix: "Fix",
  sup_no_data: "No supplier data yet. Upload a GSTR-2B to start.",
  sup_no_filter: "No suppliers match your filter.",
  sup_invoices: "Invoices",
  sup_health_score: "Health Score",
  sup_open_issues: "Open Issues",
  sup_no_invoices: "No invoices found for this supplier",

  // Action Queue
  aq_all: "All",
  aq_critical: "Critical",
  aq_high: "High",
  aq_medium: "Medium",
  aq_no_actions: "No actions needed — great compliance!",
  aq_resolve: "Resolve",
  aq_resolved: "Resolved",

  // Sidebar deadlines
  sb_upcoming_deadlines: "Upcoming Deadlines",
  sb_itc_trend: "ITC Trend (6mo)",
  sb_wa_turn_on: "Turn on for instant compliance reminders.",
  sb_wa_active: "You'll get deadline & mismatch alerts.",

  // Reports
  rep_search: "Search period…",
  rep_period: "Period",
  rep_itc_confirmed: "ITC Confirmed",
  rep_invoices: "Invoices",
  rep_issues: "Issues",
  rep_pdf: "PDF",
  rep_download: "Download PDF",
  rep_generating: "Generating PDF…",
  rep_few_seconds: "This might take a few seconds.",
  rep_gstr2b_reports: "GSTR-2B Reports",
  rep_gstr2b_subtitle: "Auto-drafted ITC records uploaded from GST portal",

  // Profile
  pro_my_profile: "My Profile",
  pro_view_edit: "View & edit your CA details",
  pro_name: "Name",
  pro_email: "Email",
  pro_phone: "Phone",
  pro_save: "Save Changes",
  pro_saved: "Saved ✅",
  pro_portfolio: "Portfolio",
  pro_total_clients: "Total Clients",
  pro_clients_with_issues: "Clients with Issues",
  pro_total_itc_at_risk: "Total ITC At Risk",

  // Filing readiness
  fr_gstr3b_readiness: "GSTR-3B Readiness",
  fr_invoices_processed: "Invoices processed",
  fr_issues_need_attention: "issues need attention →",
  fr_upload_gstr2b: "UPLOAD GSTR-2B",
  fr_json_excel: "JSON / EXCEL FROM GST PORTAL",
  fr_drop_or_click: "Drop GSTR-2B JSON/Excel · or click",
  fr_upload_start: "Upload GSTR-2B to start",
  fr_ready_to_file: "Ready to file!",

  // --- Trader PWA (/trader) -------------------------------------------
  // Shell & drawer
  tr_active: "Active",
  tr_my_business: "My Business",
  tr_language: "Language",
  tr_nav_dashboard: "Dashboard",
  tr_nav_invoice_history: "Invoice History",
  tr_nav_reports: "Reports & GSTR-2B",
  tr_log_out: "Log Out",

  // Offline queue
  tr_checking_photo_quality: "Checking photo quality on your device…",
  tr_queued_one: "1 invoice queued — will upload when back online",
  tr_queued_many: "{count} invoices queued — will upload when back online",
  tr_queued_offline_title: "Queued — Offline",
  tr_queued_offline_msg:
    "No connection — invoice queued. It'll upload automatically once you're back online.",
  tr_queued_slow_msg:
    "Upload didn't finish in time (slow connection?) — invoice queued and will retry automatically.",
  tr_queued_invoice_failed: "A queued invoice failed to process.",

  // Scan result toast
  tr_processing_invoice: "Processing invoice…",
  tr_processing_checks: "Checking GSTIN, HSN codes, GSTR-2B match",
  tr_invoice_analyzed: "Invoice Analyzed",
  tr_itc: "ITC",
  tr_narrated_on_device: "Narrated on-device",
  tr_hsn_match: "On-device HSN match",
  tr_processing_failed_title: "Processing Failed",
  tr_quota_reached: "API usage limit reached. Please try again tomorrow or contact support.",
  tr_invoice_processed: "Invoice processed!",
  tr_no_active_trader: "No active trader. Please set up your GSTIN first.",
  tr_processing_failed_retry: "Processing failed. Try again.",
  tr_location_note: "Scanned ~{km}km from where you usually scan.",

  // ITC verdict status labels (raw codes come back from the domain engine)
  tr_status_confirmed: "CONFIRMED",
  tr_status_fixable_blocked: "BLOCKED — FIXABLE",
  tr_status_at_risk: "AT RISK",
  tr_status_missed: "MISSED ITC",
  tr_status_ineligible: "INELIGIBLE",
  tr_status_fraud_flagged: "FRAUD FLAGGED",
  tr_status_duplicate: "DUPLICATE",
  tr_status_processing: "PROCESSING",
  tr_status_pending: "PENDING",

  // Home / history
  tr_financial_snapshot: "Financial Snapshot",
  tr_required_actions: "Required Actions",
  tr_invoice_history: "Invoice History",
  tr_no_invoices_yet: "No invoices processed yet. Scan your first invoice!",
  tr_unknown_supplier: "Unknown Supplier",
  tr_history: "History",

  // Scan button + on-device photo check
  tr_checking_photo: "Checking Photo…",
  tr_processing: "Processing…",
  tr_scan_invoice: "Scan Invoice",
  tr_photo_may_not_scan: "Photo may not scan well",
  tr_retake_glare:
    "Too much glare — avoid direct light or flash reflecting off the invoice, then retake.",
  tr_retake_blur: "Photo looks blurry — hold the camera steady and let it focus, then retake.",
  tr_retake_photo: "Retake Photo",
  tr_upload_anyway: "Upload Anyway",
  tr_checked_on_device: "Checked on your device — no data was uploaded for this check.",

  // --- Camera scanner (/trader/scanner) --------------------------------
  sc_align_invoice: "Align invoice within frame",
  sc_invoice_captured: "Invoice Captured",
  sc_extracted_synced:
    "Munim.ai has extracted the data and synced it with your CA's dashboard.",
  sc_supplier: "Supplier",
  sc_amount: "Amount",
  sc_gstin: "GSTIN",
  sc_scan_another: "Scan Another Invoice",

  // Common
  loading: "Loading…",
  error: "Something went wrong",
  close: "Close",
  back: "Back",
  next: "Next",
  prev: "Previous",
  // Practice view -- the CA's multi-client triage
  nav_practice: "My Practice",
  pr_title: "My Practice",
  pr_subtitle: "Every client, ranked by money at risk",
  pr_clients: "Clients",
  pr_needs_you: "Need you",
  pr_at_risk: "At risk",
  pr_unclaimed: "Unclaimed",
  pr_open_items: "Open items",
  pr_no_clients: "No clients yet",
  pr_no_clients_body: "Traders who name your number as their CA appear here automatically.",
  pr_partial: "Some clients could not be read. The totals below are incomplete.",
  pr_all_clear: "Nothing outstanding",
  pr_open_client: "Open dashboard",
  pr_view_brief: "What to do",
  pr_brief_title: "What to do first",
  pr_actionable: "Still fixable",
  pr_expired: "Window closed",
  pr_chase_by: "Chase by",
  pr_days_left: "days left",
  pr_days_ago: "days ago",
  pr_composition: "Composition scheme",
  pr_never_reconciled: "Never reconciled",
  pr_back_to_practice: "Back to practice",
  pr_last_activity: "Last invoice",
  pr_send_fix_link: "Send fix link",
  pr_link_copied: "Link copied - send it to the supplier",

  // Unclaimed credit recovery
  mi_ask: "Ask the trader",
  mi_asking: "Asking\u2026",
  mi_ask_hint: "Sends a WhatsApp message asking whether they have these bills.",
  mi_requests: "Bills we asked about",
  mi_status_asked: "Waiting for reply",
  mi_status_has_bill: "Has the bill",
  mi_status_no_bill: "No bill",
  mi_status_resolved: "Recovered",
  mi_recovered: "Recovered",
  mi_written_off: "Confirmed missing",

  // Supplier network intelligence
  net_title: "What the network sees",
  net_subtitle: "How these suppliers behave across every business Munim monitors",
  net_clean: "Files on time",
  net_mixed: "Patchy",
  net_risky: "Often defaults",
  net_unknown: "Not enough data",
  net_reportable: "suppliers with enough data to report",

  // Statutory citation
  why_title: "Why this verdict",
  why_section: "The law",
  why_means: "What it means",
  why_fix: "What fixes it",
  why_source: "Read the section",
  why_none: "Munim cannot trace this verdict to a specific clause, so it is not quoting one.",
  why_derived_status: "Inferred from the verdict, not from a recorded reason.",

};

export default en;
