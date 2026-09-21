# Security Policy

## Reporting a Vulnerability

This project handles real financial and business data for Indian MSMEs —
invoices, GSTINs, ITC amounts, supplier relationships. If you find a
security issue, please **do not open a public GitHub issue** for it.

Instead, use GitHub's [private vulnerability reporting](../../security/advisories/new)
for this repository, or reach out directly to the maintainer. Please
include:

- A description of the issue and its potential impact
- Steps to reproduce (a request/response pair, a script, whatever's
  fastest to verify with)
- Any suggested fix, if you have one

We'll acknowledge reports as quickly as we can and keep you updated as
the issue is worked on.

## Scope

This repo covers two things:

- The main product (`backend/`, `frontend/`) — FastAPI + Next.js, running
  against either Postgres or DynamoDB.
- `aws/` — a separate, AWS-native build of the invoice pipeline
  (Step Functions, Lambda, Textract, Bedrock, DynamoDB).

Both are in scope for reports.

## What's already documented

Known gaps and their status are tracked openly rather than hidden — see
the [Data Protection (DPDP Act, 2023)](README.md#data-protection-dpdp-act-2023)
section of the root README, and `aws/README.md`'s security posture and
"deliberately not built" sections. Naming a limitation there isn't a
vulnerability report; it's us being upfront about what's built and what
isn't yet.
