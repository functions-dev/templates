# Python HTTP Function - Keycloak Auth

A Knative Function that validates JWT Bearer tokens issued by a Keycloak
realm. Demonstrates how to protect HTTP endpoints with OpenID Connect (OIDC)
authentication in a serverless function.

## How It Works

```
User logs into Keycloak
  -> receives a JWT (signed with Keycloak's private key)
  -> sends request to this function with Bearer <JWT>
  -> function validates the JWT signature using Keycloak's public keys (JWKS)
  -> returns the user's identity claims
```

No shared secrets needed. The function fetches Keycloak's public signing keys
from the standard JWKS endpoint and verifies tokens locally (no per-request
calls back to Keycloak).

## Prerequisites

- A Keycloak instance (any reachable endpoint)
- `func` CLI ([github](https://github.com/knative/func/blob/main/README.md))
- `curl` and `jq` for testing

> **No Keycloak yet?** The Quick Start below runs one locally via Docker.

## Quick Start

### 1. Create the function

```bash
func create myfunc \
  -r https://github.com/functions-dev/templates \
  -l python -t keycloak-auth
cd myfunc
```

### 2. Run Keycloak locally

```bash
docker run -d --name keycloak \
  -p 18080:8080 \
  -e KC_BOOTSTRAP_ADMIN_USERNAME=admin \
  -e KC_BOOTSTRAP_ADMIN_PASSWORD=admin \
  quay.io/keycloak/keycloak:latest start-dev
```

Wait for it to start (~30-60 seconds):

```bash
until curl -sf http://localhost:18080/realms/master >/dev/null; do sleep 2; done
echo "Keycloak ready"
```

### 3. Set up a realm, client, and user

Get an admin token and create everything via the Keycloak Admin REST API:

```bash
# Admin token
ADMIN_TOKEN=$(curl -s -X POST \
  "http://localhost:18080/realms/master/protocol/openid-connect/token" \
  -d "grant_type=password" \
  -d "client_id=admin-cli" \
  -d "username=admin" \
  -d "password=admin" | jq -r '.access_token')

# Create realm
curl -sf -X POST "http://localhost:18080/admin/realms" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"realm": "myrealm", "enabled": true}'

# Create client (public, with password grant enabled)
curl -sf -X POST "http://localhost:18080/admin/realms/myrealm/clients" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "clientId": "my-func-client",
    "enabled": true,
    "publicClient": true,
    "directAccessGrantsEnabled": true
  }'

# Create user
curl -sf -X POST "http://localhost:18080/admin/realms/myrealm/users" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "firstName": "Test",
    "lastName": "User",
    "email": "testuser@example.com",
    "emailVerified": true,
    "enabled": true,
    "requiredActions": [],
    "credentials": [{
      "type": "password",
      "value": "testpassword",
      "temporary": false
    }]
  }'
```

### 4. Run the function

```bash
func run --builder=host \
  -e "KEYCLOAK_URL=http://localhost:18080" \
  -e "KEYCLOAK_REALM=myrealm"
```

This blocks the terminal. **Open a second terminal** for the next steps.

### 5. Get a token and test

In your second terminal, get a token and call the function:

```bash
# Get a token
TOKEN=$(curl -s -X POST \
  "http://localhost:18080/realms/myrealm/protocol/openid-connect/token" \
  -d "grant_type=password" \
  -d "client_id=my-func-client" \
  -d "username=testuser" \
  -d "password=testpassword" | jq -r '.access_token')

echo "$TOKEN" | cut -c1-50  # should print a long base64 string

# Public endpoint (no auth needed)
curl -s http://localhost:8080/ | jq .

# See your identity (auth required)
curl -s -H "Authorization: Bearer $TOKEN" \
  http://localhost:8080/auth/whoami | jq .

# No token -> 401
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8080/auth/whoami

# Bad token -> 403
curl -s -o /dev/null -w "%{http_code}\n" \
  -H "Authorization: Bearer fake.token.here" \
  http://localhost:8080/auth/whoami
```

> **Tip:** Keycloak access tokens expire after **5 minutes** by default.
> If you get a 401 "token expired" response, re-run the `TOKEN=...`
> command above to get a fresh one.

## Configuration

Set via environment variables or `func run -e`:

| Variable | Required | Description | Example |
|---|---|---|---|
| `KEYCLOAK_URL` | Yes | Base URL of Keycloak | `http://localhost:18080` |
| `KEYCLOAK_REALM` | Yes | Keycloak realm name | `myrealm` |
| `KEYCLOAK_AUDIENCE` | No | Expected `aud` claim | `my-func-client` |

## Endpoints

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/` | No | Function info and available endpoints |
| GET | `/auth/whoami` | Yes | Returns authenticated user's token claims |
| POST | `/auth/verify` | Yes | Validates the token and returns claims |

## Response Examples

### GET /auth/whoami (valid token)
```json
{
  "authenticated": true,
  "claims": {
    "sub": "user-uuid",
    "preferred_username": "testuser",
    "email": "testuser@example.com",
    "realm_access": {"roles": ["default-roles-myrealm"]},
    "iss": "http://localhost:18080/realms/myrealm",
    "exp": 1712345678
  }
}
```

### Missing token (401)
```json
{"error": "authentication required", "detail": "No Authorization header found"}
```

### Invalid token (403)
```json
{"error": "invalid token", "detail": "Token could not be decoded: ..."}
```

### Keycloak not configured (503)
```json
{"error": "Keycloak not configured", "hint": "Set KEYCLOAK_URL and KEYCLOAK_REALM environment variables"}
```

## Cleanup

```bash
docker rm -f keycloak
```

## Development

```bash
pip install -e '.[dev]'
pytest tests/
```

For more, see [the complete documentation](https://github.com/knative/func/tree/main/docs)
