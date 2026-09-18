# Observability

## X-Ray

Active tracing enabled on all 7 Lambdas (`munim-upload-invoice`,
`munim-whatsapp-inbound`, `munim-invoice-ingest`, `munim-extract-invoice`,
`munim-compute-verdict`, `munim-explain-verdict`, `munim-finalize-invoice`)
and on the `munim-invoice-pipeline` Step Functions state machine.

Verified live: uploading one real invoice through `munim-upload-invoice`
produces a **single X-Ray trace ID spanning all of it** --
`upload_invoice -> ingest -> Step Functions -> extract -> compute_verdict
-> explain -> finalize`, 13 segments across 6 Lambdas and the state
machine, with per-segment latency. One invoice, one trace, the whole
journey.

## CloudWatch dashboard

`munim-invoice-pipeline` (see `cloudwatch-dashboard.json` for the exact
widget definitions) -- Lambda invocations/errors/duration for every
function in the pipeline, Step Functions execution outcomes, API Gateway
request/error counts, WhatsApp inbound SNS publish counts (currently
flat at zero -- see the roadmap's decisions log for why), DynamoDB
consumed capacity, and the DLQ's current backlog.

Console: CloudWatch -> Dashboards -> `munim-invoice-pipeline`, region
`ap-south-1`.
