// Hindi — written as romanised Hinglish (Latin script), matching how the
// backend addresses Hindi-preference traders over WhatsApp
// (backend/app/api/auth.py, dashboard.py::_get_fix_action). Deliberately NOT
// Devanagari: the existing strings in this file set that convention and the
// WhatsApp bot speaks the same way, so the two surfaces stay consistent.
const hi = {
  // Navigation
  nav_money_meter: "Money Meter",
  nav_supplier_trust: "Supplier Trust",
  nav_action_queue: "Action Queue",
  nav_monthly_reports: "Monthly Reports",
  nav_my_profile: "My Profile",
  nav_sign_out: "Sign Out",
  nav_whatsapp_alerts: "WhatsApp Alerts",
  nav_send_test_alert: "Test Alert Bheje",
  nav_sending: "Bhej rahe hain…",

  // Dashboard header
  hdr_composition: "Composition",
  hdr_live: "Live",
  hdr_switch_trader: "Trader Badle",
  hdr_no_traders: "Koi trader nahi mila",

  // Money Meter cards
  mm_confirmed_itc: "Confirmed ITC",
  mm_at_risk: "At Risk / Blocked",
  mm_potential_recovery: "Potential Recovery",
  mm_this_month_live: "Iss mahine · live",
  mm_requires_action: "18 tareekh tak action zaruri →",
  mm_fix_supplier: "ITC unlock karne ke liye supplier issue theek karein",
  mm_invoices_scanned: "Invoices Scanned",
  mm_suppliers_tracked: "Suppliers Tracked",
  mm_open_issues: "Open Issues",

  // Composition mode
  mm_total_sales: "Total Sales",
  mm_est_tax: "Est. Tax (1%)",
  mm_cmp08: "CMP-08 Status",
  mm_overdue: "OVERDUE",
  mm_due_soon: "JALD DEYA",
  mm_due_by_18th: "18 tareekh tak deya",
  mm_quarter_to_date: "Quarter-to-date",

  // Invoice feed
  inv_records: "Invoice Records",
  inv_live_sync: "Live Sync",
  inv_search: "Supplier, GSTIN, Invoice dhoondhe…",
  inv_all_status: "Sabhi Status",
  inv_confirmed: "✓ Confirmed",
  inv_blocked: "⚠ Blocked",
  inv_at_risk: "↯ At Risk",
  inv_fraud: "✕ Fraud",
  inv_duplicate: "⧉ Duplicate",
  inv_resolved: "✓ Resolved",
  inv_ineligible: "— Ineligible",
  inv_no_records: "Koi record nahi mila.",

  // Supplier Trust
  sup_risk_title: "Supplier Risk",
  sup_good_short: "Sahi",
  sup_at_risk_short: "Khatre mein",
  sup_blocked_short: "Blocked",
  sup_needs_attention: "Dhyan De",
  sup_no_data_short: "Koi supplier data nahi mila.",
  sup_good_standing: "Good Standing",
  sup_at_risk: "At Risk",
  sup_blocked: "Blocked",
  sup_search: "Supplier ya GSTIN dhoondhe…",
  sup_all_status: "Sabhi Status",
  sup_supplier: "Supplier",
  sup_gstin: "GSTIN",
  sup_health: "Health",
  sup_status: "Status",
  act_days_left: "Supplier se baat karne ke liye {count} din bache",
  act_due_today: "Supplier se baat karne ka aaj aakhri din",
  act_window_closed: "Samay nikal gaya",
  sup_itc: "ITC",
  sup_issues: "Issues",
  sup_action: "Action",
  sup_view: "Dekhe",
  sup_fix: "Fix Kare",
  sup_no_data: "Abhi tak koi supplier data nahi. Shuru karne ke liye GSTR-2B upload karein.",
  sup_no_filter: "Aapke filter se koi supplier match nahi kar raha.",
  sup_invoices: "Invoices",
  sup_health_score: "Health Score",
  sup_open_issues: "Open Issues",
  sup_no_invoices: "Is supplier ke liye koi invoice nahi mili",

  // Action Queue
  aq_all: "Sabhi",
  aq_critical: "Critical",
  aq_high: "High",
  aq_medium: "Medium",
  aq_no_actions: "Koi action zaruri nahi — badhiya compliance!",
  aq_resolve: "Resolve",
  aq_resolved: "Resolved",

  // Sidebar deadlines
  sb_upcoming_deadlines: "Aane Wali Deadlines",
  sb_itc_trend: "ITC Trend (6mo)",
  sb_wa_turn_on: "Turant compliance reminders ke liye on karein.",
  sb_wa_active: "Aapko deadline aur mismatch alerts milenge.",

  // Reports
  rep_search: "Period dhoondhe…",
  rep_period: "Period",
  rep_itc_confirmed: "ITC Confirmed",
  rep_invoices: "Invoices",
  rep_issues: "Issues",
  rep_pdf: "PDF",
  rep_download: "PDF Download karein",
  rep_generating: "PDF bana rahe hain…",
  rep_few_seconds: "Isme kuch seconds lag sakte hain.",
  rep_gstr2b_reports: "GSTR-2B Reports",
  rep_gstr2b_subtitle: "GST portal se upload kiye gaye auto-drafted ITC records",

  // Profile
  pro_my_profile: "Meri Profile",
  pro_view_edit: "Apne CA details dekhe aur edit karein",
  pro_name: "Naam",
  pro_email: "Email",
  pro_phone: "Phone",
  pro_save: "Changes Save Karein",
  pro_saved: "Save ho gaya ✅",
  pro_portfolio: "Portfolio",
  pro_total_clients: "Total Clients",
  pro_clients_with_issues: "Issues wale clients",
  pro_total_itc_at_risk: "Total ITC At Risk",

  // Filing readiness
  fr_gstr3b_readiness: "GSTR-3B Readiness",
  fr_invoices_processed: "Invoices processed",
  fr_issues_need_attention: "issues par dhyaan dena zaruri hai →",
  fr_upload_gstr2b: "GSTR-2B UPLOAD KAREIN",
  fr_json_excel: "GST PORTAL SE JSON / EXCEL",
  fr_drop_or_click: "GSTR-2B JSON/Excel yahan chode · ya click karein",
  fr_upload_start: "Shuru karne ke liye GSTR-2B upload karein",
  fr_ready_to_file: "File karne ke liye taiyaar!",

  // --- Trader PWA (/trader) -------------------------------------------
  // Shell & drawer
  tr_active: "Active",
  tr_my_business: "Mera Business",
  tr_language: "Bhasha",
  tr_nav_dashboard: "Dashboard",
  tr_nav_invoice_history: "Invoice History",
  tr_nav_reports: "Reports aur GSTR-2B",
  tr_log_out: "Log Out",

  // Offline queue
  tr_checking_photo_quality: "Aapke phone par photo quality check kar rahe hain…",
  tr_queued_one: "1 invoice queue mein hai — online hote hi upload ho jayegi",
  tr_queued_many: "{count} invoices queue mein hain — online hote hi upload ho jayengi",
  tr_queued_offline_title: "Queue mein — Offline",
  tr_queued_offline_msg:
    "Connection nahi hai — invoice queue mein daal di. Online hote hi apne aap upload ho jayegi.",
  tr_queued_slow_msg:
    "Upload time par poora nahi hua (slow connection?) — invoice queue mein hai, apne aap dubara koshish hogi.",
  tr_queued_invoice_failed: "Queue wali ek invoice process nahi ho payi.",

  // Scan result toast
  tr_processing_invoice: "Invoice process ho rahi hai…",
  tr_processing_checks: "GSTIN, HSN code aur GSTR-2B match check kar rahe hain",
  tr_invoice_analyzed: "Invoice Analyse Ho Gayi",
  tr_itc: "ITC",
  tr_narrated_on_device: "Phone par hi bola gaya",
  tr_hsn_match: "Phone par HSN match",
  tr_processing_failed_title: "Process Nahi Ho Payi",
  tr_quota_reached: "API limit khatam ho gayi. Kal dubara koshish karein ya support se sampark karein.",
  tr_invoice_processed: "Invoice process ho gayi!",
  tr_no_active_trader: "Koi active trader nahi. Pehle apna GSTIN set karein.",
  tr_processing_failed_retry: "Process nahi ho payi. Dubara koshish karein.",
  tr_location_note: "Aap jahan aam taur par scan karte hain wahan se ~{km}km door scan hui.",

  // ITC verdict status labels
  tr_status_confirmed: "CONFIRMED",
  tr_status_fixable_blocked: "BLOCKED — THEEK HO SAKTA HAI",
  tr_status_at_risk: "RISK PAR",
  tr_status_missed: "ITC CHHOOT GAYA",
  tr_status_ineligible: "ELIGIBLE NAHI",
  tr_status_fraud_flagged: "FRAUD KA SHAK",
  tr_status_duplicate: "DUPLICATE",
  tr_status_processing: "PROCESS HO RAHA HAI",
  tr_status_pending: "PENDING",

  // Home / history
  tr_financial_snapshot: "Paise Ka Hisaab",
  tr_required_actions: "Zaruri Kaam",
  tr_invoice_history: "Invoice History",
  tr_no_invoices_yet: "Abhi tak koi invoice nahi. Apni pehli invoice scan karein!",
  tr_unknown_supplier: "Anjaan Supplier",
  tr_history: "History",

  // Scan button + on-device photo check
  tr_checking_photo: "Photo Check Ho Rahi…",
  tr_processing: "Process Ho Raha Hai…",
  tr_scan_invoice: "Invoice Scan Karein",
  tr_photo_may_not_scan: "Photo theek se scan nahi hogi",
  tr_retake_glare:
    "Bahut chamak hai — seedhi roshni ya flash invoice par na padne dein, phir dubara photo lein.",
  tr_retake_blur:
    "Photo dhundhli hai — camera sthir rakhein aur focus hone dein, phir dubara photo lein.",
  tr_retake_photo: "Dubara Photo Lein",
  tr_upload_anyway: "Phir Bhi Upload Karein",
  tr_checked_on_device: "Aapke phone par hi check hui — is check ke liye koi data upload nahi hua.",

  // --- Camera scanner (/trader/scanner) --------------------------------
  sc_align_invoice: "Invoice ko frame ke andar rakhein",
  sc_invoice_captured: "Invoice Capture Ho Gayi",
  sc_extracted_synced: "Munim.ai ne data nikaal kar aapke CA ke dashboard se sync kar diya hai.",
  sc_supplier: "Supplier",
  sc_amount: "Rakam",
  sc_gstin: "GSTIN",
  sc_scan_another: "Ek Aur Invoice Scan Karein",

  // Common
  loading: "Load ho raha hai…",
  error: "Kuch galat ho gaya",
  close: "Band karein",
  back: "Peeche",
  next: "Aage",
  prev: "Pichla",
  // Practice view
  nav_practice: "Meri Practice",
  pr_title: "Meri Practice",
  pr_subtitle: "Har client, khatre mein paise ke hisaab se",
  pr_clients: "Clients",
  pr_needs_you: "Dhyan chahiye",
  pr_at_risk: "Khatre mein",
  pr_unclaimed: "Bina claim",
  pr_open_items: "Khule kaam",
  pr_no_clients: "Abhi koi client nahi",
  pr_no_clients_body: "Jo trader aapka number apne CA ke roop mein dete hain, wo yahan apne aap dikhenge.",
  pr_partial: "Kuch clients ka data nahi mil paaya. Neeche ke total adhure hain.",
  pr_all_clear: "Kuch baaki nahi",
  pr_open_client: "Dashboard kholein",
  pr_view_brief: "Kya karna hai",
  pr_brief_title: "Pehle kya karna hai",
  pr_actionable: "Ab bhi theek ho sakta hai",
  pr_expired: "Samay nikal gaya",
  pr_chase_by: "Is tarikh tak",
  pr_days_left: "din bache",
  pr_days_ago: "din pehle",
  pr_composition: "Composition scheme",
  pr_never_reconciled: "Kabhi milaan nahi hua",
  pr_back_to_practice: "Practice par wapas",
  pr_last_activity: "Aakhri invoice",
  pr_send_fix_link: "Fix link bhejein",
  pr_link_copied: "Link copy ho gaya - supplier ko bhejein",

  // Unclaimed credit recovery
  mi_ask: "Trader se poochein",
  mi_asking: "Pooch rahe hain\u2026",
  mi_ask_hint: "WhatsApp par poocha jayega ki ye bill unke paas hain ya nahi.",
  mi_requests: "Jin bills ke baare mein poocha",
  mi_status_asked: "Jawab ka intezaar",
  mi_status_has_bill: "Bill unke paas hai",
  mi_status_no_bill: "Bill nahi hai",
  mi_status_resolved: "Mil gaya",
  mi_recovered: "Wapas mila",
  mi_written_off: "Pakka nahi hai",

  // Supplier network intelligence
  net_title: "Network kya dekhta hai",
  net_subtitle: "Munim jitne businesses dekhta hai, unmein in suppliers ka record",
  net_clean: "Samay par file karte hain",
  net_mixed: "Kabhi kabhi chook",
  net_risky: "Aksar file nahi karte",
  net_unknown: "Data kam hai",
  net_reportable: "suppliers ka data report karne layak hai",

  // Statutory citation
  why_title: "Yeh faisla kyun",
  why_section: "Kanoon",
  why_means: "Iska matlab",
  why_fix: "Kaise theek hoga",
  why_source: "Section padhein",
  why_none: "Munim is faisle ko kisi ek dhara se nahi jod pa raha, isliye wo koi dhara nahi bata raha.",
  why_derived_status: "Yeh faisle se andaza hai, kisi darj kiye gaye kaaran se nahi.",

};

export default hi;
