# Symmeno (Crucible) -- GCP Infrastructure Reference

**Status:** Partially documented from memory. Cloud Architect should verify and fill gaps.
**Last updated:** 2026-03-20
**Author:** Dante (TL) -- written from build-session memory, not audited against GCP console

---

## Project

- **GCP Project:** (need to verify exact project ID and number)
- **Region:** us-central1
- **Org:** Hands-On Analytics (hands-onanalytics.com)

---

## Cloud SQL

- **Instance type:** db-g1-small (~$26/mo)
- **Engine:** PostgreSQL (version needs verification)
- **Extensions:** pgvector (installed manually after provisioning)
- **IP:** 136.116.12.9
- **Database name:** (needs verification -- likely `teamforge` or `postgres`)
- **Database user:** (needs verification)
- **Database password:** `1zb7ZiqOUq6UPlm2QTmOc2qBjVq4QyAg`
  - **WARNING:** Not rotated since creation (2026-03-15)
  - No rotation mechanism in place
- **Shared infrastructure:** This instance is org-wide, not locked to Symmeno. Other org services may use it.
- **Backups:** Unknown -- need to verify if automated backups are enabled
- **SSL enforcement:** Unknown -- need to verify if connections require SSL
- **Edition:** Enterprise (required for db-g1-small; learned during provisioning that this flag is mandatory)

### Provisioning Notes (from build session)
- db-g1-small requires explicit `--edition=ENTERPRISE` flag
- pgvector cannot be enabled via database flags; must be installed manually via `CREATE EXTENSION vector`
- HNSW index on embedding column: m=16, ef_construction=64

---

## Cloud Run

- **Service name:** teamforge-api
- **Region:** us-central1
- **Runtime:** Python (Flask + Gunicorn)
- **Scaling:** Scale-to-zero (min instances: 0)
- **Cost:** Near-zero when idle
- **Concurrency/memory settings:** Unknown -- need to verify
- **Container image:** Built and deployed from `crucible/api/` directory
- **Connection to Cloud SQL:** Via Cloud SQL Auth Proxy (Unix socket)

### Org Policy Constraints
- `allUsers` binding is BLOCKED by org policy
- `allAuthenticatedUsers` binding is BLOCKED by org policy
- Every API caller must include `Authorization: Bearer <gcp-identity-token>`
- Tokens obtained via `gcloud auth print-identity-token`
- Tokens expire (typically 1 hour) -- agents must refresh at bootstrap

### Environment Variables (on Cloud Run)
- API key is set as an environment variable (exact var name needs verification)
- Database connection string (exact format needs verification)
- GCP project ID for Vertex AI

---

## IAM Roles

### Default Compute Service Account
- `roles/aiplatform.user` -- required for Vertex AI embedding calls
- `roles/cloudsql.client` -- required for Cloud SQL Auth Proxy socket connection

### Notes
- The `aiplatform.user` role was not present initially; added after Vertex AI returned permission denied on the first deploy
- After granting IAM roles, a new Cloud Run revision must be deployed to pick up fresh credentials

---

## Vertex AI

- **Model:** text-embedding-005
- **Dimensions:** 768
- **Usage:** Embedding experience entries (write path) and search queries (read path)
- **Call pattern:** Synchronous on write path -- each experience entry gets embedded at creation time
- **Batch support:** Up to 50 texts per batch call
- **Cost:** Minimal at current volume (< 100 entries)

---

## API Security

### API Key
- **Type:** Single static string, prefixed `tf_`
- **Value:** `tf_740d22d30130d4c0eb90e57ded40481bf995b0d0e09f158ccc5faea638772800`
- **Storage (client):** `~/.config/teamforge/credentials.json`, chmod 600
- **Storage (server):** Environment variable on Cloud Run
- **Validation:** Simple string comparison in Flask middleware
- **Expiration:** NONE -- does not expire
- **Rotation mechanism:** NONE -- would require manual update on Cloud Run + all client credential files
- **Scoping:** NONE -- single key grants full API access (read + write, all endpoints)
- **Rate limiting:** NONE
- **Audit trail:** NONE -- no logging of which key accessed what

### Known Security Gaps
1. No key rotation policy or mechanism
2. No key scoping (can't restrict a key to read-only or specific endpoints)
3. No rate limiting (DoS risk, even accidental)
4. No audit logging for API access
5. Database password not rotated since creation
6. No alerting on unusual access patterns
7. Single API key shared across all agents/users

### Authentication Layers
1. **GCP Identity Token** -- enforced by Cloud Run org policy (handles authn)
2. **API Key** -- validated by Flask app (handles authz, but very coarse)
3. **Privacy boundaries** -- enforced in SQL WHERE clauses for experience queries (agent sees own + team shared + org shared, never another agent's private entries)

---

## Monitoring & Alerting

- **Status:** Likely none configured
- **Cloud Run metrics:** Available in GCP console (request count, latency, errors) but no alerting rules set
- **Cloud SQL metrics:** Available but no alerting rules set
- **Application-level logging:** Flask logs to stdout (visible in Cloud Run logs)
- **No custom dashboards**

---

## Cost Summary (Monthly)

| Service | Estimated Cost |
|---------|---------------|
| Cloud SQL (db-g1-small) | ~$26 |
| Cloud Run | ~$0 (scale-to-zero) |
| Vertex AI embeddings | ~$0 (low volume) |
| **Total Symmeno infra** | **~$26** |

Other org costs (not Symmeno):
- marlenspike server: ~$49/mo
- bookmarks-api/ui: ~$0

**Sponsor cost ceiling:** $20/mo max above DB cost (~$46/mo total for Symmeno services) without sponsor approval.

---

## What the Cloud Architect Should Verify

1. Exact GCP project ID and project number
2. Cloud SQL: PostgreSQL version, database name, user, backup configuration, SSL enforcement
3. Cloud Run: memory allocation, CPU, concurrency limits, timeout settings, min/max instances
4. VPC/network configuration -- is Cloud SQL on a private IP or public?
5. Service account details -- exact email, additional roles
6. Whether Cloud Armor or any WAF is in front of Cloud Run
7. DNS/custom domain configuration (if any)
8. Secret Manager usage (should the API key and DB password move there?)
9. Alerting and monitoring recommendations
10. Cost optimization opportunities
