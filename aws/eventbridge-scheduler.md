# EventBridge Scheduler -- deadline alerts

`munim-deadline-alerts-schedule`: `cron(0 10 5,10,18 * ? *)`,
timezone `Asia/Kolkata` -- 10:00 IST on the 5th/10th/18th of each month,
same cadence as `backend/app/main.py`'s APScheduler job. Target:
`munim-deadline-alerts` Lambda.

Ports that job's exact logic, not a re-derived guess:
- `today.day <= 11` -> GSTR-1, due the 11th; else GSTR-3B, due the 20th.
- Per active trader (`munim-traders`, `status: active`), query
  `munim-invoices` (partition key `trader_id` -- a real Query, not a
  table scan) for items whose `itc_verdict.status` is `FIXABLE_BLOCKED`
  or `AT_RISK`.
- Sum `itc_verdict.itc_blocked + itc_verdict.itc_amount` across those --
  same two fields the real backend sums (`itc_amount_blocked` +
  `itc_amount_eligible`), just DynamoDB's actual field names instead of
  Supabase's flat columns. Alert only fires if that sum is > 0.

Verified live against real data: correctly found the one real
`FIXABLE_BLOCKED` invoice in the table (Rs.31,878 blocked) and correctly
computed `GSTR-3B, due in 2 days` for today's date (2026-09-18, day 18).

Sending is best-effort, not the point of this Lambda -- see the
docstring and the roadmap's decisions log for why (WhatsApp inbound is
blocked; outbound has never been tested against a real number). Tested
against a synthetic phone-shaped trader anyway: the call reached Meta's
API cleanly and came back with a real, specific validation error
("invalid destination phone number") rather than any auth/config
failure -- confirming outbound WhatsApp sending itself works from this
AWS account; only the inbound relay is broken.
