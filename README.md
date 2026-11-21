# FitAI Backend · Phase 4

FastAPI backend with goal validation, adaptive fitness assessments, persisted user-owned answers, and a conservative goal feasibility endpoint. This is a prototype, **not** medical clearance, a training prescription, or an accuracy-validated achievement-date predictor.

## Local development (Mac/Linux)

1. Install Python 3.11+ and Docker Desktop.
2. From the repository root, run `cp .env.example .env`. If you already have `.env`, edit it instead of overwriting your local settings.
3. Run `python3 -c "import secrets; print(secrets.token_urlsafe(48))"`, and paste its output into `FITAI_JWT_SECRET=` in your local `.env`. **Never commit your actual secret.**
4. Ensure `DATABASE_URL` inside `.env` uses **localhost:5433**. Docker publishes host port 5433 while the container listens on 5432.
5. Start PostgreSQL with `docker compose up -d db` (recreate existing containers if changing published ports).
6. Set up Python with `python3 -m venv .venv && source .venv/bin/activate`.
7. Install dependencies with `python -m pip install -r requirements.txt`.
8. Apply schema migrations: `python -m alembic upgrade head`.
9. Start the API: `python -m uvicorn app.main:app --reload`.
10. Open http://127.0.0.1:8000/docs.

The app automatically loads the repository-root `.env` file **before** it constructs the database engine, and shell environment variables take priority. You no longer need `source .env` just to start the Python API.

## API testing

1. Register with `POST /v1/auth/register` using `{"email":"you@example.com","password":"a-long-unique-password"}`.
2. Use the returned bearer token with the **Authorize** button in API docs.
3. Create an assessment with `POST /v1/assessments`; e.g. `{"goal_type":"handstand_hold","target_value":10,"requested_weeks":8}`.
4. Complete each question using `POST /v1/assessments/{assessment_id}/answers`.
5. Query `GET /v1/assessments/{assessment_id}/feasibility` for the conservative feasibility assessment.

Run the complete test suite with `python -m pytest -q`. Tests use isolated SQLite; GitHub Actions also runs a PostgreSQL migration smoke test.

## Security notes

- Rotate any JWT signing secret previously committed to GitHub. The historical Git commit containing a secret can remain accessible even if the current branch changes. Deleting a line in a later commit does **not** remove the leaked value from git history.
- Changing the signing secret invalidates previously issued JWTs using the old key. After rotation, restart the API and log in again.
- Never check `.env`, production credentials, or real health/assessment data into Git.
- Authentication is still a development prototype: password-reset, abuse throttling, email verification, account deletion, and additional security and privacy controls are not yet implemented. Do not expose this app publicly as a consumer health service.
- The old assessment API now requires authentication. Goal preview remains public.
