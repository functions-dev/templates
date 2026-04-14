#!/bin/bash
#
# E2E test for python/keycloak-auth
#
# Spins up a real Keycloak instance in Docker, creates a realm + client + user,
# gets a real token, starts the function, and calls it with that token.
#
# This tests the one thing unit tests can't: the actual JWKS fetch from a
# real Keycloak server and end-to-end token validation.
#
# Expects these vars from run-e2e.sh:
#   REPO_ROOT, LANGUAGE, TEMPLATE, FUNC_BIN, TEMPLATE_REPO, VERBOSE
#
# Prerequisites:
#   - docker (or podman)
#   - func CLI installed
#   - curl, jq

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKDIR=$(mktemp -d)
LISTEN_ADDRESS="${LISTEN_ADDRESS:-127.0.0.1:8080}"
KC_PORT="${KC_PORT:-18080}"
KC_CONTAINER="keycloak-e2e-$$" #keycloak-e2e-54321 (shell's PID, unique per run)
RUN_PID=""

# Keycloak test config
KC_ADMIN_USER="admin"
KC_ADMIN_PASS="admin"
KC_REALM="e2e-test"
KC_CLIENT_ID="func-client"
KC_TEST_USER="testuser"
KC_TEST_PASS="testpassword"

if [[ "$VERBOSE" == "true" ]]; then OUT=/dev/stdout; else OUT=/dev/null; fi

# Container runtime choice
if command -v docker &>/dev/null; then
    CONTAINER_RT=docker
elif command -v podman &>/dev/null; then
    CONTAINER_RT=podman
else
    echo "FAIL: docker or podman required"
    exit 1
fi

cleanup() {
    if [[ -n "$RUN_PID" ]] && ps -p "$RUN_PID" > /dev/null 2>&1; then
        kill "$RUN_PID" 2>/dev/null || true
        wait "$RUN_PID" 2>/dev/null || true
    fi
    lsof -ti ":${LISTEN_ADDRESS##*:}" 2>/dev/null | xargs kill 2>/dev/null || true
    $CONTAINER_RT rm -f "$KC_CONTAINER" &>/dev/null || true
    rm -rf "$WORKDIR"
}
trap cleanup EXIT

KC_URL="http://localhost:$KC_PORT"

# ─── 1. Start Keycloak ──────────────────────────────────────
echo "[1/6] Starting Keycloak..."

$CONTAINER_RT run -d --name "$KC_CONTAINER" \
    -p "$KC_PORT:8080" \
    -e KC_BOOTSTRAP_ADMIN_USERNAME="$KC_ADMIN_USER" \
    -e KC_BOOTSTRAP_ADMIN_PASSWORD="$KC_ADMIN_PASS" \
    quay.io/keycloak/keycloak:latest start-dev >"$OUT"

# Wait for Keycloak to be ready (can take 30-60s)
for i in $(seq 1 60); do
    if curl -sf "$KC_URL/realms/master" &>/dev/null; then
        break
    fi
    if [[ $i -eq 60 ]]; then
        echo "FAIL: Keycloak did not start within 120s"
        exit 1
    fi
    sleep 2
done

echo "  OK (Keycloak ready at $KC_URL)"

# ─── 2. Configure Keycloak (realm, client, user) ────────────
echo "[2/6] Configuring Keycloak realm..."

# Get admin token
ADMIN_TOKEN=$(curl -sf -X POST \
    "$KC_URL/realms/master/protocol/openid-connect/token" \
    -d "grant_type=password" \
    -d "client_id=admin-cli" \
    -d "username=$KC_ADMIN_USER" \
    -d "password=$KC_ADMIN_PASS" | jq -r '.access_token')

if [[ -z "$ADMIN_TOKEN" || "$ADMIN_TOKEN" == "null" ]]; then
    echo "FAIL: Could not get admin token"
    exit 1
fi

# Create realm
curl -sf -X POST "$KC_URL/admin/realms" \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"realm\": \"$KC_REALM\", \"enabled\": true}" >"$OUT"

# Create public client (no client secret needed for password grant)
curl -sf -X POST "$KC_URL/admin/realms/$KC_REALM/clients" \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{
        \"clientId\": \"$KC_CLIENT_ID\",
        \"enabled\": true,
        \"publicClient\": true,
        \"directAccessGrantsEnabled\": true
    }" >"$OUT"

# Create test user
curl -sf -X POST "$KC_URL/admin/realms/$KC_REALM/users" \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{
        \"username\": \"$KC_TEST_USER\",
        \"firstName\": \"Test\",
        \"lastName\": \"User\",
        \"email\": \"testuser@example.com\",
        \"emailVerified\": true,
        \"enabled\": true,
        \"requiredActions\": [],
        \"credentials\": [{
            \"type\": \"password\",
            \"value\": \"$KC_TEST_PASS\",
            \"temporary\": false
        }]
    }" >"$OUT"

echo "  OK (realm=$KC_REALM, client=$KC_CLIENT_ID, user=$KC_TEST_USER)"

# ─── 3. Get a real user token ───────────────────────────────
echo "[3/6] Getting user token from Keycloak..."

TOKEN_RESPONSE=$(curl -s -X POST \
    "$KC_URL/realms/$KC_REALM/protocol/openid-connect/token" \
    -d "grant_type=password" \
    -d "client_id=$KC_CLIENT_ID" \
    -d "username=$KC_TEST_USER" \
    -d "password=$KC_TEST_PASS")

USER_TOKEN=$(echo "$TOKEN_RESPONSE" | jq -r '.access_token')

if [[ -z "$USER_TOKEN" || "$USER_TOKEN" == "null" ]]; then
    echo "FAIL: Could not get user token"
    echo "  Response: $TOKEN_RESPONSE"
    exit 1
fi

echo "  OK (got token, $(echo "$USER_TOKEN" | wc -c | tr -d ' ') bytes)"

# ─── 4. Create function from template ───────────────────────
echo "[4/6] Creating function from template..."

cd "$WORKDIR"
$FUNC_BIN create e2e-test -r "$TEMPLATE_REPO" -l "$LANGUAGE" -t "$TEMPLATE" >"$OUT"
cd e2e-test

echo "  OK"

# ─── 5. Start function server ───────────────────────────────
echo "[5/6] Starting function server..."

if lsof -ti ":${LISTEN_ADDRESS##*:}" &>/dev/null; then
    echo "FAIL: Port ${LISTEN_ADDRESS##*:} is already in use"
    exit 1
fi

LISTEN_ADDRESS="$LISTEN_ADDRESS" \
    $FUNC_BIN run --builder=host \
    -e "KEYCLOAK_URL=$KC_URL" \
    -e "KEYCLOAK_REALM=$KC_REALM" >"$OUT" 2>&1 &
RUN_PID=$!

for i in $(seq 1 30); do
    if curl -sf "http://$LISTEN_ADDRESS/" &>/dev/null; then
        break
    fi
    if ! ps -p "$RUN_PID" > /dev/null 2>&1; then
        echo "FAIL: func run process died"
        exit 1
    fi
    sleep 2
done

if ! curl -sf "http://$LISTEN_ADDRESS/" &>/dev/null; then
    echo "FAIL: Function server did not start within 60s"
    exit 1
fi

echo "  OK"

# ─── 6. Test the function ───────────────────────────────────
echo "[6/6] Running tests..."

BASE="http://$LISTEN_ADDRESS"

# 6a. Public endpoint (no auth)
echo "  [a] GET / (public) ..."
RESP=$(curl -sf "$BASE/")
echo "$RESP" | jq -e '.name == "keycloak-auth"' >"$OUT"
echo "    OK → 200"

# 6b. Auth with valid token
echo "  [b] GET /auth/whoami (valid token) ..."
RESP=$(curl -sf -H "Authorization: Bearer $USER_TOKEN" "$BASE/auth/whoami")
echo "$RESP" | jq -e '.authenticated == true' >"$OUT"
echo "$RESP" | jq -e '.claims.preferred_username == "testuser"' >"$OUT"
echo "    OK → 200, username=testuser"

# 6c. No token
echo "  [c] GET /auth/whoami (no token) ..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$BASE/auth/whoami")
if [[ "$HTTP_CODE" != "401" ]]; then
    echo "    FAIL: expected 401, got $HTTP_CODE"
    exit 1
fi
echo "    OK → 401"

# 6d. Garbage token
echo "  [d] GET /auth/whoami (garbage token) ..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
    -H "Authorization: Bearer this.is.garbage" "$BASE/auth/whoami")
if [[ "$HTTP_CODE" != "403" ]]; then
    echo "    FAIL: expected 403, got $HTTP_CODE"
    exit 1
fi
echo "    OK → 403"

# 6e. Valid token again (function still works after bad requests)
echo "  [e] GET /auth/whoami (valid token again) ..."
RESP=$(curl -sf -H "Authorization: Bearer $USER_TOKEN" "$BASE/auth/whoami")
echo "$RESP" | jq -e '.authenticated == true' >"$OUT"
echo "    OK → 200"

echo ""
echo "=== PASS ==="
