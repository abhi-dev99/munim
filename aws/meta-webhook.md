# munim-meta-webhook -- direct Meta webhook (WhatsApp bypass)

## Why this exists

AWS End User Messaging Social's own inbound relay (WABA event
destination -> SNS -> `munim-whatsapp-inbound`) is stuck: every AWS-side
setting is confirmed correct via both the API and the console's own
health dashboard (WABA Active, phone number Healthy, event destination
Configured, SNS topic policy correct, subscription active, IAM correct)
-- yet zero events have ever arrived from Meta, across multiple real
test messages over two days. See the roadmap's decisions log for the
full diagnosis; this is not a config bug on our side, and it isn't
diagnosable further without AWS Support.

Rather than keep waiting on an unexplained third-party relay,
`munim-meta-webhook` receives Meta's WhatsApp Cloud API webhook
**directly** -- the same way this product's own FastAPI backend already
does successfully via ngrok (`backend/app/api/webhook.py` +
`backend/app/services/whatsapp.py`). Ported logic, not re-derived:
same GET verification handshake, same `X-Hub-Signature-256` HMAC
check, same webhook payload shape, same Graph API media-download flow.

**One deliberate improvement over the ported code**: that codebase's
signature check fails *open* if `META_APP_SECRET` is empty and
`ENVIRONMENT=development` (a documented P0). This Lambda never does
that -- an empty or wrong secret fails **closed** (every request
rejected), verified live.

## Infra

- Lambda: `munim-meta-webhook`, role `munim-lambda-meta-webhook`
  (`dynamodb:GetItem` on `munim-traders` only, `s3:PutObject` on the
  invoices bucket only, KMS decrypt/generate-data-key, X-Ray write --
  no `social-messaging:*` permissions at all, since this Lambda talks
  to Meta's Graph API directly and never touches AWS End User Messaging
  Social).
- API Gateway (REST, regional): `munim-meta-webhook-api`, id
  `a0dsr3hjkb`. `GET /webhook` (Meta's verification handshake) and
  `POST /webhook` (real events), both `AWS_PROXY` to the Lambda, no API
  key -- Meta authenticates itself via the verify token (GET) and the
  HMAC signature (POST), not our API-key scheme.
  Invoke URL: `https://a0dsr3hjkb.execute-api.ap-south-1.amazonaws.com/prod/webhook`

Verified live:
- `GET ?hub.mode=subscribe&hub.verify_token=<correct>&hub.challenge=X` -> echoes `X` back, `200`.
- Same with a wrong verify token -> `403`.
- `POST` with no `X-Hub-Signature-256` header -> `403`.
- `POST` with a wrong signature -> `403`.

## The phone-number catch

`backend/.env`'s Meta credentials (`META_PHONE_NUMBER_ID`) belong to a
**different number** than the one linked to AWS End User Messaging
Social (`+1 555-495-4380`). The AWS-linked number's Meta App is one AWS
itself created and owns during the embedded signup flow -- there's no
console access to register a custom webhook on that specific app at
all. So this workaround can only receive events for the *existing
backend's own number/app*, not the AWS-linked one.

That means registering this Lambda's URL as that app's webhook
**replaces** the existing ngrok -> FastAPI backend as the receiver for
that number, for as long as it stays registered -- only one webhook URL
can be active per app at a time. Not additive; a swap.

## Still needed before this goes live (blocked on the user, not on infra)

1. The real `META_APP_SECRET` from Meta's developer console (App
   Settings -> Basic -> App secret) -- currently deployed empty, which
   is why it correctly fails closed on every real request right now.
2. Confirmation that swapping the webhook off the existing backend (see
   above) is acceptable for however long this is being used.
3. Once both are set: register in Meta's dashboard (App -> WhatsApp ->
   Configuration -> Webhook) -- Callback URL
   `https://a0dsr3hjkb.execute-api.ap-south-1.amazonaws.com/prod/webhook`,
   Verify token `munim_verify_2026`, subscribe to the **messages** field.
