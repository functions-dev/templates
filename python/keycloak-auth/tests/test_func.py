"""Tests for the keycloak-auth function.

Tests run WITHOUT a real Keycloak server — we generate our own RSA key pair,
sign JWTs with the private key (playing Keycloak), and mock PyJWKClient to
return our public key.

Tests are structured as scenarios that mirror real usage: one function
instance handling a sequence of requests, just like production.
"""

import time
from unittest.mock import MagicMock, patch

import jwt as pyjwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

from function import new


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

TEST_PRIVATE_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
TEST_PUBLIC_KEY = TEST_PRIVATE_KEY.public_key()
TEST_KEYCLOAK_URL = "https://keycloak.example.com"
TEST_REALM = "testrealm"
TEST_ISSUER = f"{TEST_KEYCLOAK_URL}/realms/{TEST_REALM}"


def make_jwt(claims: dict, private_key=None) -> str:
    """Sign a JWT with the given key (default: our test key)."""
    if private_key is None:
        private_key = TEST_PRIVATE_KEY
    pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    return pyjwt.encode(claims, pem, algorithm="RS256", headers={"kid": "test-key-id"})


def make_claims(**overrides) -> dict:
    """Build a valid Keycloak-like claims dict."""
    now = int(time.time())
    claims = {
        "sub": "user-uuid-1234",
        "preferred_username": "testuser",
        "email": "testuser@example.com",
        "iss": TEST_ISSUER,
        "iat": now,
        "exp": now + 3600,
        "realm_access": {"roles": ["user"]},
    }
    claims.update(overrides)
    return claims


def make_scope(path: str = "/", method: str = "GET", token: str = "") -> dict:
    """Build an ASGI scope dict."""
    headers = []
    if token:
        headers.append([b"authorization", f"Bearer {token}".encode()])
    return {"method": method, "path": path, "headers": headers, "query_string": b""}


class ResponseCapture:
    """Captures ASGI send() calls."""

    def __init__(self):
        self.status = None
        self.body = b""

    async def __call__(self, message):
        if message["type"] == "http.response.start":
            self.status = message["status"]
        elif message["type"] == "http.response.body":
            self.body += message.get("body", b"")

    @property
    def json(self) -> dict:
        import json
        return json.loads(self.body)


def make_configured_function():
    """Create a Function with mocked JWKS (no network calls)."""
    f = new()
    with patch("function.keycloak_auth.PyJWKClient") as mock_cls:
        mock_key = MagicMock()
        mock_key.key = TEST_PUBLIC_KEY
        mock_cls.return_value.get_signing_key_from_jwt.return_value = mock_key
        f.start({"KEYCLOAK_URL": TEST_KEYCLOAK_URL, "KEYCLOAK_REALM": TEST_REALM})
    return f


async def call(f, path="/", method="GET", token=""):
    """Helper: call the function and return the captured response."""
    resp = ResponseCapture()
    await f.handle(make_scope(path, method, token), None, resp)
    return resp


# ---------------------------------------------------------------------------
# Scenario 1: Deployed without config → everything fails gracefully
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="function")
async def test_unconfigured_deployment():
    """Operator deploys the function but forgets KEYCLOAK_URL/REALM."""
    f = new()
    f.start({})

    # ready() should say no — platform won't route traffic yet
    ok, msg = f.ready()
    assert ok is False

    # but if a request sneaks through, auth endpoints return 503 not a crash
    resp = await call(f, "/auth/whoami")
    assert resp.status == 503

    # the public root endpoint still works though
    resp = await call(f, "/")
    assert resp.status == 200


# ---------------------------------------------------------------------------
# Scenario 2: Legitimate user flow
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="function")
async def test_legitimate_user_flow():
    """User gets a token from Keycloak and calls protected endpoints."""
    f = make_configured_function()

    # function is ready
    ok, _ = f.ready()
    assert ok is True

    # user has a valid token
    token = make_jwt(make_claims())

    # GET /auth/whoami → see my identity
    resp = await call(f, "/auth/whoami", token=token)
    assert resp.status == 200
    assert resp.json["claims"]["preferred_username"] == "testuser"
    assert resp.json["claims"]["email"] == "testuser@example.com"

    # POST /auth/verify → confirm token is valid
    resp = await call(f, "/auth/verify", method="POST", token=token)
    assert resp.status == 200
    assert resp.json["valid"] is True


# ---------------------------------------------------------------------------
# Scenario 3: Attacker tries various bad tokens
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="function")
async def test_rejected_tokens():
    """Various invalid tokens are all rejected by the same function instance."""
    f = make_configured_function()

    # no token at all → 401
    resp = await call(f, "/auth/whoami")
    assert resp.status == 401

    # expired token (exp 1 hour ago) → 401
    expired = make_jwt(make_claims(exp=int(time.time()) - 3600))
    resp = await call(f, "/auth/whoami", token=expired)
    assert resp.status == 401
    assert "expired" in resp.json["error"]

    # token signed with a completely different RSA key → 403
    attacker_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    forged = make_jwt(make_claims(), private_key=attacker_key)
    resp = await call(f, "/auth/whoami", token=forged)
    assert resp.status == 403

    # garbage string as token → 403
    resp = await call(f, "/auth/whoami", token="not.a.jwt")
    assert resp.status == 403

    # and after all those attacks, a valid token still works
    good_token = make_jwt(make_claims())
    resp = await call(f, "/auth/whoami", token=good_token)
    assert resp.status == 200
    assert resp.json["authenticated"] is True
