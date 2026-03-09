"""
Shared pytest fixtures for exercising FastAPI routers over the running API service.
"""

from __future__ import annotations

import hashlib
import os
import sqlite3
import uuid
from collections.abc import AsyncGenerator
from datetime import datetime, timezone
from pathlib import Path

import httpx
import pytest
import pytest_asyncio
from dotenv import load_dotenv

# Load project and test specific environment variables.
load_dotenv(".env", override=False)
load_dotenv("test/.env.test", override=False)

API_BASE_URL = os.getenv("TEST_BASE_URL", "http://localhost:5050").rstrip("/")
_ADMIN_LOGIN_ENV = os.getenv("TEST_USERNAME")
_ADMIN_PASSWORD_ENV = os.getenv("TEST_PASSWORD")
ADMIN_LOGIN = _ADMIN_LOGIN_ENV or "pytest_admin"
ADMIN_PASSWORD = _ADMIN_PASSWORD_ENV or "PytestAdmin!123"

_ADMIN_TOKEN_CACHE: str | None = None
HTTP_TIMEOUT = httpx.Timeout(30.0, connect=5.0)


def _ensure_test_admin_user() -> None:
    """Create or update a test superadmin account for API integration tests."""
    save_dir = os.getenv("SAVE_DIR", "saves")
    db_path = Path(save_dir) / "database" / "server.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)

    salt = os.urandom(32).hex()
    password_hash = f"{hashlib.sha256((ADMIN_PASSWORD + salt).encode()).hexdigest()}:{salt}"
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE user_id = ?", (ADMIN_LOGIN,))
        row = cursor.fetchone()

        if row:
            cursor.execute(
                """
                UPDATE users
                SET username = ?,
                    password_hash = ?,
                    role = 'superadmin',
                    is_deleted = 0,
                    deleted_at = NULL,
                    login_failed_count = 0,
                    last_failed_login = NULL,
                    login_locked_until = NULL
                WHERE user_id = ?
                """,
                (ADMIN_LOGIN, password_hash, ADMIN_LOGIN),
            )
        else:
            cursor.execute(
                """
                INSERT INTO users (
                    username, user_id, password_hash, role, created_at, last_login,
                    login_failed_count, is_deleted
                ) VALUES (?, ?, ?, 'superadmin', ?, ?, 0, 0)
                """,
                (ADMIN_LOGIN, ADMIN_LOGIN, password_hash, now, now),
            )

        conn.commit()


@pytest_asyncio.fixture(scope="function")
async def test_client() -> AsyncGenerator[httpx.AsyncClient, None]:
    """Async HTTP client bound to the live API base URL."""
    async with httpx.AsyncClient(base_url=API_BASE_URL, timeout=HTTP_TIMEOUT, follow_redirects=True) as client:
        yield client


@pytest_asyncio.fixture(scope="function")
async def admin_token() -> str:
    """Authenticate with super admin credentials and cache the bearer token."""
    global _ADMIN_TOKEN_CACHE

    if _ADMIN_TOKEN_CACHE:
        return _ADMIN_TOKEN_CACHE

    if not (_ADMIN_LOGIN_ENV and _ADMIN_PASSWORD_ENV):
        _ensure_test_admin_user()

    async with httpx.AsyncClient(
        base_url=API_BASE_URL, timeout=HTTP_TIMEOUT, follow_redirects=True
    ) as bootstrap_client:
        response = await bootstrap_client.post(
            "/api/auth/token", data={"username": ADMIN_LOGIN, "password": ADMIN_PASSWORD}
        )

        if response.status_code == 401:
            # Auto-bootstrap a deterministic test admin account when credentials are unknown.
            _ensure_test_admin_user()
            response = await bootstrap_client.post(
                "/api/auth/token", data={"username": ADMIN_LOGIN, "password": ADMIN_PASSWORD}
            )

        if response.status_code == 429:
            retry_after = int(response.headers.get("Retry-After", "2"))
            _ensure_test_admin_user()
            await asyncio.sleep(max(1, retry_after))
            response = await bootstrap_client.post(
                "/api/auth/token", data={"username": ADMIN_LOGIN, "password": ADMIN_PASSWORD}
            )

        if response.status_code == 401:
            first_run_response = await bootstrap_client.get("/api/auth/check-first-run")
            if first_run_response.status_code == 200 and first_run_response.json().get("first_run", False):
                pytest.fail(
                    "Super admin account has not been initialized. Please complete `/api/auth/initialize` "
                    "before running router tests."
                )

    if response.status_code != 200:
        pytest.fail(f"Failed to authenticate as admin (status={response.status_code}): {response.text}")

    token = response.json().get("access_token")
    if not token:
        pytest.fail("Admin authentication did not return an access token.")

    _ADMIN_TOKEN_CACHE = token
    return token


@pytest.fixture(scope="function")
def admin_headers(admin_token: str) -> dict[str, str]:
    """Authorization headers for the super admin user."""
    return {"Authorization": f"Bearer {admin_token}"}


@pytest_asyncio.fixture(scope="function")
async def standard_user(test_client: httpx.AsyncClient, admin_headers: dict[str, str]) -> dict:
    """
    Provision a temporary standard user for permission checks.

    Yields a dictionary with `user`, `password`, and `headers` keys.
    """
    username = f"pytest_user_{uuid.uuid4().hex[:8]}"
    password = f"Pw!{uuid.uuid4().hex[:8]}"

    response = await test_client.post(
        "/api/auth/users",
        json={"username": username, "password": password, "role": "user"},
        headers=admin_headers,
    )
    if response.status_code != 200:
        pytest.fail(f"Failed to create standard user (status={response.status_code}): {response.text}")

    user_payload = response.json()
    login_response = await test_client.post(
        "/api/auth/token",
        data={"username": user_payload["user_id"], "password": password},
    )
    if login_response.status_code != 200:
        pytest.fail(
            f"Failed to authenticate as standard user (status={login_response.status_code}): {login_response.text}"
        )

    access_token = login_response.json().get("access_token")
    if not access_token:
        pytest.fail("Standard user login succeeded but no access token was returned.")

    try:
        yield {
            "user": user_payload,
            "password": password,
            "headers": {"Authorization": f"Bearer {access_token}"},
        }
    finally:
        response = await test_client.delete(f"/api/auth/users/{user_payload['id']}", headers=admin_headers)
        assert response.status_code == 200, f"Failed to cleanup test user {user_payload['user_id']}: {response.text}"


@pytest_asyncio.fixture(scope="function")
async def knowledge_database(test_client: httpx.AsyncClient, admin_headers: dict[str, str]) -> dict:
    """
    Create a temporary knowledge database for tests that need LightRAG metadata.
    """
    db_name = f"pytest_kb_{uuid.uuid4().hex[:6]}"
    embed_model_name = "siliconflow/BAAI/bge-m3"

    config_response = await test_client.get("/api/system/config", headers=admin_headers)
    if config_response.status_code == 200:
        config_payload = config_response.json()
        embed_choices = (
            config_payload.get("_config_items", {})
            .get("embed_model", {})
            .get("choices", [])
        )
        if embed_choices:
            embed_model_name = embed_choices[0]
        elif config_payload.get("embed_model"):
            embed_model_name = config_payload["embed_model"]

    create_response = await test_client.post(
        "/api/knowledge/databases",
        json={
            "database_name": db_name,
            "description": "Pytest managed knowledge base",
            "embed_model_name": embed_model_name,
            "kb_type": "lightrag",
            "additional_params": {},
        },
        headers=admin_headers,
    )
    if create_response.status_code != 200:
        pytest.fail(
            f"Failed to create knowledge database (status={create_response.status_code}): {create_response.text}"
        )

    db_payload = create_response.json()
    if db_payload.get("status") == "failed":
        pytest.fail(f"Failed to create knowledge database: {db_payload}")

    if "db_id" not in db_payload:
        pytest.fail(f"Knowledge database payload missing db_id: {db_payload}")

    db_id = db_payload["db_id"]
    db_payload["name"] = db_payload.get("name") or db_name

    try:
        yield db_payload
    finally:
        await test_client.delete(f"/api/knowledge/databases/{db_id}", headers=admin_headers)


def pytest_configure(config: pytest.Config) -> None:
    """Register commonly used custom markers."""
    config.addinivalue_line("markers", "auth: marks tests that require authentication")
    config.addinivalue_line("markers", "integration: marks tests that hit the live API service")


pytest_plugins = ["pytest_asyncio"]
