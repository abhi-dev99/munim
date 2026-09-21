# Contributing to Munim-AI

Thanks for taking a look at this project. It started as a WeMakeDevs x AWS
"First Commit" hackathon submission — see the root [README](README.md) for
what it does and [`aws/README.md`](aws/README.md) for the AWS-native build
specifically.

## Ground rules

- Open an issue before a large change so we can agree on direction first.
  Small fixes (typos, dependency bumps, obvious bugs) can go straight to a
  PR.
- Keep PRs scoped to one change. A bug fix doesn't need to also refactor
  the surrounding code.
- This project follows the [Code of Conduct](CODE_OF_CONDUCT.md).

## Local setup

**Backend** (FastAPI):

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

**Frontend** (Next.js):

```bash
cd frontend
npm install
npm run dev
```

The backend talks to either Supabase/Postgres or DynamoDB depending on the
`DATA_BACKEND` env var (`app/services/db.py`) — you don't need AWS
credentials to run the Postgres path locally. The AWS-native pipeline in
`aws/` is a separate, self-contained build; see `aws/README.md` for how to
exercise it without needing the full backend running.

## Making a change

1. Fork the repo and create a branch off `main`.
2. Make your change. If it touches deterministic compliance logic
   (`backend/app/domain/`), add or update a test — that code has zero
   tolerance for silent behavior changes.
3. Run the existing test suite (`cd backend && pytest`, `cd frontend && npm test`)
   before opening a PR.
4. Open a PR against `main` using the PR template. Describe *why*, not just
   *what* — the diff already shows what changed.

## Reporting bugs

Open an issue with: what you expected, what happened instead, and steps to
reproduce. For anything security-sensitive, please don't open a public
issue — see the security notes in the root README's DPDP section instead
and reach out directly.
