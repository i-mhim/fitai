# FitAI Backend · Phase 3

FastAPI backend with goal validation, conditional fitness assessments, **durable assessment storage** and **authenticated account ownership**. This is a prototype, not a medical screening or exercise prescription system.

## Local development (Mac/Linux)

1. Install Python 3.11+ and Docker Desktop.
2. Copy `.env.example` to `.env`; replace `FITAI_JWT_SECRET` with a random secret from `python3 -c "import secrets; print(secrets.token_urlsafe(48))"`.
3. Load environment variables in your shell: `set -a; source .env; set +a` (the sample values contain no shell metacharacters).
4. `docker compose up -d db`
5. `python3 -m venv .venv && source .venv/bin/activate`
6. `pip install -r requirements.txt`
7. `alembic upgrade head`
8. `python -m uvicorn app.main:app --reload`
9. Open http://127.0.0.1:8000/docs

## API testing

1. `POST /v1/auth/register` with `{"email":"you@example.com","password":"a-long-unique-password"}`.
2. Copy the returned access token, click **Authorize** in the docs, and paste the token (FastAPI may show a bearer-token field).
3. `POST /v1/assessments` with `{"goal_type":"handstand_hold","target_value":10,"requested_weeks":8}`.
4. Use the assessment ID for `/next`, `/answers` and `/summary`.
5. Restart the server; your assessment should still be stored in PostgreSQL.

Run tests with `python -m pytest -q`. Tests use an isolated SQLite database and **do not need Docker**.

## Important

- The project is now rooted at the backend (`app/`, `tests/`, `requirements.txt`). Run the commands from this repository root.
- Never commit `.env`, production credentials or real assessment health data.
- Auth is minimal: no password reset, email verification, refresh tokens, MFA, account deletion, abuse throttling, or production monitoring yet. Do not deploy publicly until those are addressed. For sensitive health data, additional privacy and security review is required.
- The old unauthenticated assessment endpoints now require `Authorization: Bearer <token>`. Goal preview remains public.
- Existing `__pycache__` files previously committed on `main` are removed in this branch and prevented by `.gitignore`.
