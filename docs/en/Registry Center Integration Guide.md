# Registry Center Third-Party Integration Guide

Registry Center exposes the integration API on a dedicated HTTPS listener. OAuth 2.0 Client Credentials is the recommended integration: obtain an access token and send it using the RFC 6750 form:

```http
Authorization: Bearer <access-token>
```

Registry Center is an OAuth 2.0 Resource Server. It validates tokens; it does not issue tokens or implement interactive login flows.

## Authentication modes

### OAuth 2.0 JWT

```properties
integration.auth.mode=oauth2_jwt
integration.auth.fingerprint_key=${INTEGRATION_FINGERPRINT_KEY}
integration.oauth2.issuer=https://iam.example.com
integration.oauth2.audience=registry-center
integration.oauth2.jwks_uri=https://iam.example.com/.well-known/jwks.json
integration.oauth2.algorithms=RS256
integration.auth.scope_role.registry.admin=nms_oss
integration.auth.scope_role.registry.vendor=vendor_agent
integration.auth.scope_role.registry.read=partner_service
integration.auth.scope_role.registry.audit=analytics_tool
```

The server validates the signature, algorithm, issuer, audience and time claims. JWKS `kid` rotation is supported. Unmapped scopes grant no role.

### OAuth 2.0 Token Introspection

```properties
integration.auth.mode=oauth2_introspection
integration.auth.fingerprint_key=${INTEGRATION_FINGERPRINT_KEY}
integration.oauth2.introspection_uri=https://iam.example.com/oauth2/introspect
integration.oauth2.client_id=${OAUTH_CLIENT_ID}
integration.oauth2.client_secret=${OAUTH_CLIENT_SECRET}
integration.oauth2.issuer=https://iam.example.com
integration.oauth2.audience=registry-center
```

Use this mode for opaque tokens. The endpoint must use HTTPS. Timeouts, malformed responses and inactive tokens fail closed. Active results are cached only briefly and never beyond token expiry.

### Static Bearer Token

For deployments without an OAuth 2.0 server, store only an HMAC-SHA-256 token digest:

```properties
credential.operations.identity=operations-service
credential.operations.token_hash=<64-lowercase-hex-digest>
credential.operations.role=nms_oss
```

```properties
integration.auth.mode=static_bearer
integration.auth.fingerprint_key=${INTEGRATION_FINGERPRINT_KEY}
integration.auth.static.hmac_key=${INTEGRATION_TOKEN_HMAC_KEY}
integration.credential.file=etc/conf/integration_credentials.conf
```

Run `python -m agent_registry.integration.token_digest` to generate a digest interactively. Never place a plaintext token in configuration, command lines, logs, or audit records.

### mTLS

```properties
integration.auth.mode=mtls
integration.client_cert=true
```

Identity is derived from the verified TLS peer certificate, never from a client-supplied HTTP header. Map certificate CN values in the credential file:

```properties
credential.vendor.identity=vendor-service
credential.vendor.cn=vendor-service.example
credential.vendor.role=vendor_agent
```

## Client Credentials example

```bash
curl -u "$CLIENT_ID:$CLIENT_SECRET" \
  -d 'grant_type=client_credentials&scope=registry.read' \
  https://iam.example.com/oauth2/token

curl -H "Authorization: Bearer $ACCESS_TOKEN" \
  https://registry.example.com:5001/integration/v1/agent-cards
```

## Error and security semantics

- `401`: missing, malformed, invalid, expired, or unverifiable credential.
- `403`: authenticated identity lacks the mapped permission.
- `429`: pre-authentication or identity rate limit exceeded.
- Responses, logs, and audit records never contain a complete token.
- JWT, introspection, and static-token validation all fail closed.

## Private authentication protocols

Private headers are not part of the core contract. Inject them through `CredentialExtractor` and `AuthenticationProvider`; see `samples/custom_auth_provider.py`. Extensions return the same `Principal`, so authorization, throttling, bans, and auditing do not inspect private request fields.

## Migration

The former private two-header scheme is no longer built into the core. Prefer OAuth 2.0 Client Credentials. A deployment that cannot migrate immediately can package its old protocol as a business-owned extractor/provider. Integration API paths and the four-role authorization matrix remain unchanged.
