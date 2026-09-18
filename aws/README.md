# Munim.ai on AWS

This is the AWS-native rebuild of [Munim.ai](https://github.com/abhi-dev99/munim-ai)'s
invoice pipeline, built for the WeMakeDevs x AWS "First Commit" hackathon.
Munim is a WhatsApp-first GST compliance co-pilot for Indian MSMEs -- it
reads a shopkeeper's purchase invoices, tells them exactly how much Input
Tax Credit (ITC) they can legally claim, flags the ones that are fraudulent
or defective, and does it the moment the invoice arrives instead of once a
month at deadline rush.

Everything on this branch lives in `aws/`. It does not touch the rest of
this repo, and it is not yet merged into `main`.

## The pipeline, in one line

```
S3 (invoice image) --> Step Functions --> DynamoDB (verdict)
       ^
       |
  two independent ways in:
  1. WhatsApp (Meta) -- linked, gated, currently blocked by a relay
     issue on Meta/AWS's side, not ours (see "Known issues" below)
  2. API Gateway -- POST /invoices, fully working, API-key gated
```

Once an image lands in S3, one Step Functions execution runs it through
four Lambdas, each doing exactly one job:

| Stage | Lambda | Job |
|---|---|---|
| 1 | `munim-extract-invoice` | Textract `AnalyzeExpense` pulls line items, amounts, and the supplier's GSTIN. No LLM involved -- this is OCR, not generation. |
| 2 | `munim-compute-verdict` | Deterministic §16/§17(5) ITC rules + Benford's-law fraud scoring + real HSN-code validation. Zero AI. This is the part that has to be trustworthy. |
| 3 | `munim-explain-verdict` | Bedrock (Amazon Nova Micro) turns the verdict into one plain Hinglish sentence for a shopkeeper. The *only* place an LLM touches this pipeline, and it only ever explains an already-computed answer -- it can't change the verdict. |
| 4 | `munim-finalize-invoice` | Writes the final verdict back to DynamoDB. |

A fifth Lambda, `munim-invoice-ingest`, sits between S3 and Step Functions:
it writes an idempotent `RECEIVED` record and kicks off the execution.

## Two ways in, on purpose

**WhatsApp** is the real product's front door, and it's linked and
configured correctly on the AWS side (`munim-whatsapp-inbound` Lambda,
subscribed to the WABA's event destination via SNS). But inbound messages
from Meta are currently not reaching AWS at all -- confirmed via zero SNS
publishes and zero Lambda invocations across multiple real test messages,
while the WhatsApp side shows the messages as delivered. Everything
checkable on our end (event destination, SNS subscription, IAM) is
correctly configured; this points to a break in Meta/AWS's own relay,
outside what's diagnosable or fixable from this account. Outbound sending
was tested separately and works fine (see `eventbridge-scheduler.md`) --
it's specifically inbound delivery that's broken.

Rather than let a demo depend on a third party's unexplained outage,
**`munim-upload-invoice`** behind a new API Gateway REST API
(`POST /invoices`) is a second, fully AWS-native way into the exact same
pipeline. See `api-gateway.md` for the request shape and how to call it.

Both paths write to the same S3 bucket under the same
`{trader_id}/{file}` key convention and trigger the same, unmodified
pipeline downstream.

## Security posture

- **Everything encrypted at rest** with one customer-managed KMS key
  (`alias/munim-s3-key`), used by S3, every DynamoDB table, and CloudTrail's
  log bucket. `abhi` is the sole key administrator; every Lambda role gets
  usage-only grants (`Decrypt`/`GenerateDataKey`), never administrative
  ones.
- **Every IAM role is scoped to exactly what its Lambda does.**
  `munim-compute-verdict` is genuinely zero-permission pure compute except
  for one `GetItem` on the HSN table it was recently given; no Lambda in
  this pipeline has broad or wildcard resource access.
- **Anti-abuse gate on both trigger paths**: `munim-traders` (DynamoDB) is
  the single source of truth for "who is a real, active trader." WhatsApp
  inbound and the API upload path both check it before doing anything that
  costs money (Textract, Bedrock) -- a stranger messaging the WhatsApp
  number, or an unknown `trader_id` hitting the API, gets rejected before
  any paid call happens. The registration check fails **closed** (a lookup
  error is treated as unregistered); infra-error checks elsewhere (like HSN
  validation) fail **open** on purpose, so an AWS-side outage never
  manufactures a compliance defect on someone's real invoice.
- **API Gateway's own key + usage plan** (`rateLimit=2/s, burst=5,
  quota=200/day`) rejects an unauthenticated caller before the Lambda ever
  runs -- a second, independent layer on top of the trader-registration
  check, not a substitute for it.
- **CloudTrail** logs every management-plane action account-wide, plus
  every `GetObject`/`PutObject` on the invoices bucket specifically --
  including root's own access -- to a separate, encrypted, public-blocked
  bucket.
- **GuardDuty** enabled account-wide.
- Region is `ap-south-1` (Mumbai), not the default `us-east-1` -- deliberately,
  for India-resident data processing under the DPDP Act, and because AWS's
  own "India geographic cross-Region inference" for Bedrock exists
  specifically for this.

## Observability

Active X-Ray tracing on every Lambda and the Step Functions state machine.
One invoice produces **one trace ID spanning the entire journey** --
upload/WhatsApp -> ingest -> Step Functions -> extract -> compute-verdict
-> explain -> finalize -- with full per-stage latency. A CloudWatch
dashboard (`munim-invoice-pipeline`) covers invocations, errors, Step
Functions outcomes, API Gateway traffic, DynamoDB capacity, and the DLQ
backlog in one pane. See `observability.md`.

## What's deliberately not built, and why

Matching the real backend's own documented philosophy: an honest gap beats
a fabricated result.

- **HSN validation checks existence only, not rate mismatch.** Textract's
  `AnalyzeExpense` has no field for the tax rate actually applied on a line
  item, so there's nothing honest to compare the correct rate against.
  Comparing "correct rate" alone with no applied rate would be a fabricated
  signal, not a real check.
- **No GSTIN registry, no GSTR-2B reconciliation, no gstin_age/
  business_mismatch fraud signals.** All of these need a real external data
  source (a GSTIN registry API, uploaded GSTR-2B data) that doesn't exist
  in this build yet. The domain logic already handles "no data" honestly
  (an untriggered placeholder signal, not a guessed score) because the real
  backend has to handle incomplete invoices anyway.
- **Cognito custom WhatsApp-OTP auth and Amplify Hosting**: on hold,
  waiting on WhatsApp inbound actually working end to end.

## Trying it yourself

```bash
curl -X POST "https://1zm28mbqwb.execute-api.ap-south-1.amazonaws.com/prod/invoices" \
  -H "x-api-key: <ask for the demo key>" \
  -H "Content-Type: application/json" \
  -d '{
    "trader_id": "<a trader_id already registered in munim-traders>",
    "content_type": "image/jpeg",
    "content_base64": "<base64-encoded invoice photo>"
  }'
```

A registered `trader_id` returns `202` immediately; the pipeline finishes
in a few seconds and the verdict lands in DynamoDB (`munim-invoices`,
partition key `trader_id`, sort key `invoice_id`).

## More detail

- [`api-gateway.md`](api-gateway.md) -- the upload endpoint, request shape, security layers
- [`observability.md`](observability.md) -- X-Ray + the CloudWatch dashboard
- [`eventbridge-scheduler.md`](eventbridge-scheduler.md) -- the scheduled deadline-alert job, ported from the real backend
- [`state-machine.json`](state-machine.json) -- the Step Functions definition
- [`lambdas/`](lambdas/) -- every Lambda's source
