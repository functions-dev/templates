"""Keycloak-authenticated HTTP function.

A Knative Function that validates JWT Bearer tokens issued by a Keycloak
realm.  Demonstrates how to protect HTTP endpoints with OIDC authentication
in a serverless function.

Endpoints:
    GET  /                → public info about this function (no auth)
    GET  /auth/whoami     → returns the authenticated user's token claims
    POST /auth/verify     → validates a token and returns its claims

All /auth/* endpoints require a valid "Authorization: Bearer <token>" header.

Configuration (environment variables):
    KEYCLOAK_URL      → base URL of Keycloak (e.g. https://keycloak.example.com)
    KEYCLOAK_REALM    → realm name (e.g. myrealm)
    KEYCLOAK_AUDIENCE → optional: expected 'aud' claim in the token
"""

import json
import logging

from .keycloak_auth import (
    KeycloakAuthenticator,
    TokenExpired,
    TokenInvalid,
    TokenMissing,
)


def new():
    """Entry point — called once by the Knative Functions runtime."""
    return Function()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def send_json(send, body: dict, status: int = 200) -> None:
    """Send a JSON response through the ASGI interface.

    ASGI (Asynchronous Server Gateway Interface) is the protocol between
    the web server and your Python function.  Every response is two messages:
        1. http.response.start  → status code + headers
        2. http.response.body   → the actual bytes
    """
    payload = json.dumps(body).encode()
    await send({
        "type": "http.response.start",
        "status": status,
        "headers": [
            [b"content-type", b"application/json"],
        ],
    })
    await send({
        "type": "http.response.body",
        "body": payload,
    })


def extract_bearer_token(scope: dict) -> str:
    """Extract the Bearer token from the ASGI scope's headers.

    ASGI headers are a list of [name, value] pairs, both as bytes.
    We're looking for:  [b"authorization", b"Bearer eyJhbG..."]

    Args:
        scope: The ASGI scope dict (contains method, path, headers, etc.)

    Returns:
        The raw JWT string (without the "Bearer " prefix).

    Raises:
        TokenMissing: No Authorization header, or not a Bearer token.
    """
    # ASGI stores headers as a list of 2-element byte lists:
    #   [[b"host", b"example.com"], [b"authorization", b"Bearer xyz"], ...]
    headers = scope.get("headers", [])

    for name, value in headers:
        if name.lower() == b"authorization":
            decoded = value.decode()

            # Must start with "Bearer " (case-sensitive per RFC 6750)
            if decoded.startswith("Bearer "):
                token = decoded[7:]  # skip "Bearer "
                if token:
                    return token

            raise TokenMissing(
                "Authorization header must use Bearer scheme"
            )

    raise TokenMissing("No Authorization header found")


def get_path(scope: dict) -> str:
    """Extract the request path from the ASGI scope."""
    return scope.get("path", "/")


# ---------------------------------------------------------------------------
# The Function
# ---------------------------------------------------------------------------

class Function:
    """Keycloak-authenticated HTTP function.

    Lifecycle (managed by the Knative Functions runtime):
        1. new()        → creates this instance
        2. start(cfg)   → called with env vars — we set up the authenticator
        3. handle(...)  → called on every HTTP request
        4. stop()       → called on shutdown
    """

    def __init__(self):
        self.auth = None          # Set up in start() with config
        self._configured = False  # Track whether Keycloak config was provided

    async def handle(self, scope, receive, send) -> None:
        """Handle an HTTP request.

        This is the ASGI handler — the runtime calls it for every request.

        Args:
            scope:   Dict with request metadata (method, path, headers, etc.)
            receive: Async callable to read the request body
            send:    Async callable to send the response
        """
        method = scope.get("method", "GET")
        path = get_path(scope)

        # --- Public endpoint: function info (no auth required) ---
        if path == "/":
            return await send_json(send, {
                "name": "keycloak-auth",
                "description": "Keycloak-authenticated HTTP function",
                "endpoints": {
                    "GET /": "This info (public)",
                    "GET /auth/whoami": "Your token claims (auth required)",
                    "POST /auth/verify": "Validate a token (auth required)",
                },
                "configured": self._configured,
            })

        # --- All /auth/* endpoints require authentication ---
        if not path.startswith("/auth"):
            return await send_json(send, {"error": "Not found"}, status=404)

        # Check that Keycloak is configured
        if not self._configured or self.auth is None:
            return await send_json(send, {
                "error": "Keycloak not configured",
                "hint": "Set KEYCLOAK_URL and KEYCLOAK_REALM environment variables",
            }, status=503)

        # --- Extract and validate the Bearer token ---
        try:
            token = extract_bearer_token(scope)
            claims = self.auth.validate_token(token)

        except TokenMissing as e:
            return await send_json(send, {
                "error": "authentication required",
                "detail": str(e),
            }, status=401)

        except TokenExpired as e:
            return await send_json(send, {
                "error": "token expired",
                "detail": str(e),
            }, status=401)

        except TokenInvalid as e:
            return await send_json(send, {
                "error": "invalid token",
                "detail": str(e),
            }, status=403)

        # --- Token is valid — dispatch to the right endpoint ---

        if path == "/auth/whoami" and method == "GET":
            # Return the user's claims from the token.
            # Typical Keycloak claims include:
            #   sub               → user UUID
            #   preferred_username → human-readable username
            #   email             → user's email
            #   realm_access      → {roles: ["user", "admin", ...]}
            #   iss               → issuer URL
            #   exp               → expiry timestamp
            return await send_json(send, {
                "authenticated": True,
                "claims": claims,
            })

        elif path == "/auth/verify" and method == "POST":
            # Just confirm the token is valid and return the claims
            return await send_json(send, {
                "valid": True,
                "claims": claims,
            })

        else:
            return await send_json(send, {"error": "Not found"}, status=404)

    def start(self, cfg) -> None:
        """Called when the function starts — configure the authenticator.

        Args:
            cfg: Dict of environment variables. The runtime passes this
                 (usually a copy of os.environ) so you don't access
                 os.environ directly.
        """
        keycloak_url = cfg.get("KEYCLOAK_URL", "")
        realm = cfg.get("KEYCLOAK_REALM", "")

        if not keycloak_url or not realm:
            logging.warning(
                "KEYCLOAK_URL and/or KEYCLOAK_REALM not set. "
                "Auth endpoints will return 503."
            )
            self._configured = False
            return

        audience = cfg.get("KEYCLOAK_AUDIENCE", "")

        self.auth = KeycloakAuthenticator(
            keycloak_url=keycloak_url,
            realm=realm,
            audience=audience,
        )
        self._configured = True

        logging.info(
            "Keycloak auth configured: realm=%s url=%s audience=%s",
            realm, keycloak_url, audience or "(any)",
        )

    def stop(self) -> None:
        """Called when the function stops."""
        logging.info("Function stopping")

    def alive(self) -> tuple:
        """Liveness check — is the process healthy?"""
        return True, "Alive"

    def ready(self) -> tuple:
        """Readiness check — can we serve traffic?

        We report not-ready if Keycloak isn't configured, so the
        platform won't route traffic to us until config is provided.
        """
        if not self._configured:
            return False, "Keycloak not configured"
        return True, "Ready"
