"""Use an isolated SQLite database; authenticate existing assessment API tests."""
import os
import tempfile
from pathlib import Path
from uuid import uuid4
import pytest

_TEST_DIR = Path(tempfile.mkdtemp(prefix="fitai-tests-"))
os.environ["DATABASE_URL"] = f"sqlite:///{_TEST_DIR / 'tests.db'}"
os.environ["FITAI_JWT_SECRET"] = "testing-only-secret-not-valid-for-production-use"

from app.core.db import Base, engine  # noqa: E402
from app.core import models  # noqa: E402, F401


@pytest.fixture(scope="session", autouse=True)
def test_schema():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(autouse=True)
def auth_for_legacy_assessment_tests(request):
    """Give original assessment tests fresh credentials without changing their assertions."""
    if request.module.__name__ != "test_assessments":
        yield
        return
    client = request.module.client
    email = f"tester-{uuid4()}@example.com"
    response = client.post("/v1/auth/register", json={"email": email, "password": "a-good-test-password"})
    assert response.status_code == 201, response.text
    client.headers["Authorization"] = f"Bearer {response.json()['access_token']}"
    yield
    client.headers.pop("Authorization", None)
