# munim-invoice-api

REST API (regional), API Gateway, id `1zm28mbqwb` in `ap-south-1`.

- `POST /invoices` -> Lambda proxy integration -> `munim-upload-invoice`
- API key required on the method (`apiKeyRequired: true`) -- confirmed
  live: a call with no key returns `403` from API Gateway itself, before
  the Lambda ever runs.
- Usage plan `munim-invoice-api-plan`: throttle `rateLimit=2, burstLimit=5`,
  quota `200/day` -- caps how much a single leaked demo key could ever
  cost, the same reasoning as the WhatsApp trader-registration gate.
- Invoke URL: `https://1zm28mbqwb.execute-api.ap-south-1.amazonaws.com/prod/invoices`

Request body (JSON):

```json
{
  "trader_id": "pipeline-test-trader",
  "content_type": "image/jpeg",
  "content_base64": "<base64-encoded image or PDF bytes>"
}
```

`trader_id` must already exist in `munim-traders` with `status: active` --
same registry the WhatsApp inbound path checks, so both trigger paths
share one source of truth for "who is a real trader." A registered
`trader_id` writes straight to the invoices bucket; the existing S3 event
notification takes it from there, unchanged.

Built as a second, fully AWS-native path into the pipeline so a demo
never depends on WhatsApp/Meta's relay being up -- see the roadmap's
decisions log entry, 2026-09-18, for why.
