"""
Munim-AI — AWS Lambda entrypoint for the dashboard API.

Wraps app/lambda_main.py's FastAPI app (the slim, dashboard-only app --
see that file's docstring for why it's separate from app/main.py) with
Mangum, an ASGI-to-Lambda adapter. This lets the existing FastAPI routers
(dashboard.py, gstr2b.py, reports.py, communications.py, auth.py) and all
the domain logic underneath them (reconciler, fraud scorer, ITC engine)
run in Lambda essentially unchanged -- the only new code in this whole
migration is the DynamoDB adapter (services/dynamodb_client.py) those
routers now call through services/db.py instead of talking to Supabase
directly.

lifespan="off": a Lambda container isn't guaranteed to stay warm between
invocations, so app/main.py's APScheduler-based startup (which only makes
sense on an always-running process) is skipped entirely here -- it was
never imported by lambda_main.py in the first place.
"""

from mangum import Mangum

from app.lambda_main import app

handler = Mangum(app, lifespan="off")
