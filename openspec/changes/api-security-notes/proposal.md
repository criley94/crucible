# API Security Notes

## What

Document the current API authentication security posture, known gaps, and future hardening roadmap.

## Why

The sponsor asked about API key storage, expiration, and security holes. This change captures the current state and known gaps so the team has a clear record of what's been deferred and what needs attention before any production-grade deployment.

## Current State

### What's Working Well
- API keys are SHA-256 hashed in the database (raw key never stored server-side)
- Keys are org-scoped (one key = one org's data)
- Keys have `is_active` flag for revocation
- `last_used_at` tracking for activity monitoring
- Dual-auth in practice: API key + GCP identity token required. The API key is enforced at the application layer (auth middleware). The GCP identity token is enforced at the infrastructure layer by GCP org policy (which blocks allUsers/allAuthenticatedUsers IAM bindings on Cloud Run services), even though cloudbuild.yaml deploys with `--allow-unauthenticated`
- GCP tokens expire hourly -- even a leaked API key is useless without valid GCP credentials
- Credentials file stored at ~/.config/teamforge/credentials.json with chmod 600

### Known Gaps (Future Hardening)
1. **No key expiration.** Keys live forever unless manually revoked. Should add `expires_at` column and enforce at middleware.
2. **No key rotation endpoint.** Rotating requires direct DB access. Should add admin API for key management (generate, rotate, revoke).
3. **Single key per org.** If compromised, all org data is exposed until manual rotation. Should support multiple active keys per org for zero-downtime rotation.
4. **No rate limiting.** API has no request throttling. Should add per-key rate limits.
5. **Raw key in conversation context.** API key appears in curl commands within CLAUDE.md and agent files. If conversation logs are stored externally, the key could be exposed there. Mitigation: the GCP token requirement makes the API key alone insufficient.
6. **No audit logging.** API tracks `last_used_at` but doesn't log individual requests with key identity. Should add request-level audit trail.

### Risk Assessment
Current risk is **low** for the following reasons:
- This is an internal tool with a single user (the sponsor)
- GCP identity token is the primary security gate (hourly expiration, requires Google account)
- The API key is a secondary factor, not the sole authentication
- Cloud Run is not publicly accessible without GCP credentials (org policy blocks allUsers/allAuthenticatedUsers IAM bindings, overriding the `--allow-unauthenticated` flag in cloudbuild.yaml)

### When to Harden
These gaps should be addressed before:
- Adding additional users or orgs
- Exposing the API outside the current GCP project
- Building the management console (Wave 4)

### Cloud Run Auth Clarification

The `cloudbuild.yaml` deployment uses `--allow-unauthenticated`, which would normally make the Cloud Run service publicly accessible without IAM auth. However, the GCP org policy for Hands-On Analytics blocks adding `allUsers` or `allAuthenticatedUsers` as invokers on Cloud Run services. The net effect:

- **cloudbuild.yaml says:** `--allow-unauthenticated` (no IAM enforcement at Cloud Run level)
- **GCP org policy enforces:** IAM authentication required (blocks the unauthenticated access)
- **Result:** Dual-auth is enforced. Callers must provide both a valid GCP identity token (satisfies IAM) and a valid API key (satisfies application middleware)

The `--allow-unauthenticated` flag is not a security hole -- it is overridden by org policy. But it is misleading in the deployment configuration. If the org policy were ever relaxed, the service would become publicly accessible with only API key auth. This is acceptable for Phase 1 but should be monitored.

### Auth Middleware Implementation

The application-level auth middleware (`api/app/middleware/auth.py`) performs:
1. Extract `X-API-Key` from request headers
2. SHA-256 hash the key
3. Look up the hash in the `api_keys` table (must be active)
4. Set `g.org_id` from the matched key record
5. Update `last_used_at` timestamp

The middleware does NOT validate the GCP identity token -- that is handled entirely by the Cloud Run infrastructure layer. The `Authorization: Bearer` header passes through the middleware untouched.

## Blocking Questions

None. This is documentation only.
