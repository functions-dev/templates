"""Keycloak JWT validation via OIDC public keys (JWKS).

This module validates Bearer tokens issued by a Keycloak realm without
needing client credentials.  It fetches the realm's public signing keys
from the standard JWKS endpoint and verifies JWT signatures locally.

Flow:
    1. On startup, configure with KEYCLOAK_URL + KEYCLOAK_REALM.
    2. On each request, call validate_token(token_string).
    3. PyJWKClient fetches (and caches) the realm's public keys.
    4. PyJWT verifies the signature, expiry, and issuer.
    5. Returns the decoded claims dict or raises an error.

No network call to Keycloak per-request — keys are cached and only
refreshed when an unknown key-id (kid) appears (e.g. after key rotation).
"""

import jwt                      # PyJWT — the JWT decode/verify library
from jwt import PyJWKClient     # Fetches JWKS and caches public keys


# ---------------------------------------------------------------------------
# Custom exceptions — so callers can distinguish *why* auth failed
# ---------------------------------------------------------------------------

class AuthError(Exception):
    """Base class for authentication errors."""
    pass


class TokenMissing(AuthError):
    """No token was provided in the request."""
    pass


class TokenExpired(AuthError):
    """The token's 'exp' claim is in the past."""
    pass


class TokenInvalid(AuthError):
    """The token is malformed, has a bad signature, wrong issuer, etc."""
    pass


class AuthNotConfigured(AuthError):
    """Keycloak URL/realm not set — can't validate anything."""
    pass


# ---------------------------------------------------------------------------
# The authenticator
# ---------------------------------------------------------------------------

class KeycloakAuthenticator:
    """Validates JWTs issued by a Keycloak realm.

    Usage:
        auth = KeycloakAuthenticator(
            keycloak_url="https://keycloak.example.com",
            realm="myrealm",
        )
        claims = auth.validate_token("eyJhbG...")
        print(claims["preferred_username"])  # → "john"

    How JWKS caching works (handled by PyJWKClient):
        - First call fetches keys from the JWKS endpoint and caches them.
        - Subsequent calls use the cache (no network hit).
        - If a token arrives with an unknown 'kid' (key ID), PyJWKClient
          automatically re-fetches the JWKS — this handles key rotation.
        - Cache lifetime is ~5 minutes by default.
    """

    def __init__(self, keycloak_url: str, realm: str, audience: str = ""):
        # Strip trailing slash for clean URL construction
        self.keycloak_url = keycloak_url.rstrip("/")
        self.realm = realm
        self.audience = audience

        # The issuer claim ('iss') Keycloak puts in every token.
        # It's always: {base_url}/realms/{realm}
        self.issuer = f"{self.keycloak_url}/realms/{self.realm}"

        # JWKS endpoint — where Keycloak publishes its public signing keys.
        # This is a standard OIDC endpoint; every OIDC provider has one.
        jwks_url = f"{self.issuer}/protocol/openid-connect/certs"

        # PyJWKClient will:
        #   1. GET the JWKS URL
        #   2. Parse the JSON → extract RSA/EC public keys
        #   3. Cache them (keyed by 'kid')
        #   4. Auto-refresh if it sees an unknown 'kid'
        self.jwks_client = PyJWKClient(jwks_url)

    def validate_token(self, token: str) -> dict:
        """Validate a JWT string and return the decoded claims.

        Args:
            token: The raw JWT string (without "Bearer " prefix).

        Returns:
            dict: The decoded token claims, e.g.:
                {
                    "sub": "user-uuid",
                    "preferred_username": "john",
                    "email": "john@example.com",
                    "realm_access": {"roles": ["user"]},
                    "iss": "https://keycloak.example.com/realms/myrealm",
                    "exp": 1712345678,
                    ...
                }

        Raises:
            TokenExpired: Token's 'exp' claim is in the past.
            TokenInvalid: Bad signature, wrong issuer, malformed, etc.
        """
        try:
            # Step 1: Get the signing key that matches this token's 'kid'.
            #
            # The JWT header contains a 'kid' (key ID) field that says
            # "I was signed with key XYZ".  PyJWKClient looks up that kid
            # in its cached JWKS and returns the matching public key.
            signing_key = self.jwks_client.get_signing_key_from_jwt(token)

            # Step 2: Decode and verify the token.
            #
            # jwt.decode() does ALL of these checks:
            #   - Verifies the signature using the public key
            #   - Checks 'exp' (expiration) — rejects expired tokens
            #   - Checks 'iss' (issuer) — must match our Keycloak realm
            #   - Checks 'aud' (audience) — if we configured one
            #   - Checks 'iat' (issued at) and 'nbf' (not before)
            #
            # algorithms=["RS256"] — Keycloak signs with RSA by default.
            # We explicitly list allowed algorithms to prevent algorithm
            # confusion attacks (where an attacker tricks you into using
            # a weaker algorithm like HS256 with the public key as secret).
            decode_options = {
                "verify_aud": bool(self.audience),
            }

            claims = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                issuer=self.issuer,
                audience=self.audience if self.audience else None,
                options=decode_options,
            )

            return claims

        except jwt.ExpiredSignatureError:
            raise TokenExpired("Token has expired")

        except jwt.InvalidIssuerError:
            raise TokenInvalid(
                f"Token issuer does not match. Expected: {self.issuer}"
            )

        except jwt.InvalidAudienceError:
            raise TokenInvalid(
                f"Token audience does not match. Expected: {self.audience}"
            )

        except jwt.DecodeError as e:
            raise TokenInvalid(f"Token could not be decoded: {e}")

        except jwt.InvalidTokenError as e:
            # Catch-all for any other JWT validation error
            raise TokenInvalid(f"Token is invalid: {e}")

        except Exception as e:
            # Network errors fetching JWKS, etc.
            raise TokenInvalid(f"Token validation failed: {e}")
