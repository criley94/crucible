# Infrastructure Consultation: Wave 1 Foundation

**From:** Cloud Architect (org-level)
**To:** Dante (TL, Nautilus)
**Date:** 2026-03-15
**Re:** Five infrastructure questions for TeamForge Phase 1

---

## 1. Cloud SQL Tier: db-f1-micro vs db-g1-small

**Recommendation: db-g1-small (~$26/mo).**

Here's the math on why.

db-f1-micro has a hard limit of 25 concurrent connections. Your SQLAlchemy pool config is pool_size=5, max_overflow=10, which means a single Cloud Run instance can hold up to 15 connections. That's fine for one instance. But Cloud Run autoscales -- if you get two concurrent instances (which can happen even at low traffic, e.g., one instance is still draining while a new one spins up), you're at 30 potential connections against a 25 limit. Connection failures will cascade: SQLAlchemy raises `OperationalError`, your health check fails, Cloud Run marks the instance unhealthy, restarts it, and the restart opens more connections. It's a bad spiral.

db-g1-small gives you 50 connections. That's headroom for 3 concurrent Cloud Run instances without stress. At Phase 1 traffic (internal use, Claude Code as the only client), you won't normally need 3 instances. But you need the headroom for deployment rollovers, health check connections, and Alembic migration connections (which run alongside the live service during deploy).

**The $19/mo difference buys you "never debug connection limit issues."** That's worth it.

**Fallback option:** If you absolutely must minimize cost, you can use db-f1-micro with pool_size=3, max_overflow=5 (8 connections per instance) and set Cloud Run max-instances=2 (16 connections max, under the 25 limit). But you're flying close to the ceiling. I don't recommend it.

**Action required before provisioning:** The Cloud SQL Admin API (`sqladmin.googleapis.com`) is not enabled in `deckhouse-489723`. I confirmed this just now. You'll need to enable it:

```bash
gcloud services enable sqladmin.googleapis.com --project=deckhouse-489723
```

This is free and takes about 30 seconds.

---

## 2. Cloud Run to Cloud SQL Connectivity

**Recommendation: Cloud SQL Auth Proxy as a Cloud Run sidecar.**

Here's the tradeoff table:

| Approach | Setup complexity | Latency | Cost | Security |
|----------|-----------------|---------|------|----------|
| Cloud SQL Auth Proxy (sidecar) | Low -- add a container to Cloud Run service definition | Negligible (~1-2ms overhead) | Free (it's a Google-provided container) | IAM-based auth, encrypted connection, no password in env vars |
| Private IP via VPC connector | Medium -- create VPC, Serverless VPC Access connector, configure Cloud SQL private IP | None (direct TCP) | ~$6-7/mo for the VPC connector (e2-micro instances) | Network-level isolation, but still need DB credentials |

The Auth Proxy wins on three counts:

1. **Cost.** The proxy sidecar is free. A VPC connector costs money.
2. **Simplicity.** No VPC setup, no subnet planning, no firewall rules. You add a container to your Cloud Run service YAML and you're done.
3. **Security.** The proxy uses the Cloud Run service account's IAM role to authenticate to Cloud SQL. No database password needed in env vars. The connection is encrypted end-to-end without needing to configure SSL certificates.

The "latency" argument against the Auth Proxy is overstated. The proxy runs as a sidecar in the same Cloud Run instance -- it's localhost communication. The overhead is 1-2ms per connection establishment, not per query. With connection pooling, you establish connections rarely.

**Private IP becomes the right choice when:** you have multiple services in a VPC that all need to talk to each other and to Cloud SQL. Phase 1 has one service. No VPC needed.

**Cloud Run config (relevant portion):**

```yaml
apiVersion: serving.knative.dev/v1
kind: Service
metadata:
  annotations:
    run.googleapis.com/launch-stage: BETA
spec:
  template:
    metadata:
      annotations:
        run.googleapis.com/cloudsql-instances: deckhouse-489723:us-central1:INSTANCE_NAME
    spec:
      containers:
        - image: YOUR_API_IMAGE
          env:
            - name: DB_HOST
              value: /cloudsql/deckhouse-489723:us-central1:INSTANCE_NAME
```

Cloud Run has native Cloud SQL Auth Proxy integration -- you don't even need to add a separate sidecar container. You add the `run.googleapis.com/cloudsql-instances` annotation and Cloud Run handles the proxy automatically. The database connection uses a Unix socket at `/cloudsql/INSTANCE_CONNECTION_NAME`.

---

## 3. Vertex AI text-embedding API

**Status: NOT enabled.** I confirmed that `aiplatform.googleapis.com` is not in the enabled API list for `deckhouse-489723`.

**To enable:**

```bash
gcloud services enable aiplatform.googleapis.com --project=deckhouse-489723
```

**Cost:** Enabling the API is free. You only pay for usage.

**textembedding-gecko@003 pricing:**
- $0.025 per 1,000 queries (as of current pricing)
- Phase 1 won't use embeddings (that's Wave 2). When you do, the volume will be small: ~10 agents, experience data written after sessions, search queries during sessions.
- Rough estimate: even at 1,000 embedding operations/month, that's $0.025/mo. Effectively free at your scale.

**Effort:** Zero operational effort. It's a managed API. You call it with the Vertex AI Python SDK or REST. No infrastructure to provision. The service account needs the `aiplatform.user` role:

```bash
gcloud projects add-iam-policy-binding deckhouse-489723 \
  --member="serviceAccount:1019921786449-compute@developer.gserviceaccount.com" \
  --role="roles/aiplatform.user"
```

**My recommendation:** Enable the API now. It costs nothing to have enabled. When Wave 2 starts, the access is already there and you avoid blocking on API enablement during development.

---

## 4. Cloud Build Trigger Configuration

**Recommendation: cloudbuild.yaml in the repo root, scoped to the api/ subdirectory.**

Here's what I'd set up:

**Trigger configuration:**
- **Event:** Push to `main` branch
- **Included files filter:** `api/**` -- the trigger only fires when files under `api/` change. Pushing a spec change or README update does not trigger a build.
- **Config file:** `cloudbuild.yaml` at the repo root (Cloud Build expects this location by default)

**cloudbuild.yaml structure:**

```yaml
steps:
  # Build the Docker image
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'us-central1-docker.pkg.dev/deckhouse-489723/demo-repo/teamforge-api:$COMMIT_SHA', '-f', 'api/Dockerfile', 'api/']

  # Push to Artifact Registry
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'us-central1-docker.pkg.dev/deckhouse-489723/demo-repo/teamforge-api:$COMMIT_SHA']

  # Run database migrations
  - name: 'us-central1-docker.pkg.dev/deckhouse-489723/demo-repo/teamforge-api:$COMMIT_SHA'
    entrypoint: 'python'
    args: ['-m', 'flask', 'db', 'upgrade']
    env:
      - 'FLASK_APP=app'
    # DB connection via Cloud SQL proxy managed by Cloud Build

  # Deploy to Cloud Run
  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    args:
      - 'gcloud'
      - 'run'
      - 'deploy'
      - 'teamforge-api'
      - '--image=us-central1-docker.pkg.dev/deckhouse-489723/demo-repo/teamforge-api:$COMMIT_SHA'
      - '--region=us-central1'
      - '--platform=managed'

images:
  - 'us-central1-docker.pkg.dev/deckhouse-489723/demo-repo/teamforge-api:$COMMIT_SHA'
```

**Why one cloudbuild.yaml at the root, not inside api/:**
- Cloud Build trigger config points to a file path relative to the repo root. Putting it at the root is the default and least surprising.
- The `api/` path prefix in build commands and the included files filter handle the subdirectory scoping.
- When you add the console (Wave 4), you add a second trigger with `console/**` filter and a separate `cloudbuild-console.yaml` at the root. Clean separation.

**Artifact Registry note:** The existing `demo-repo` in `us-central1` is available. You can use it or create a `teamforge` repo for cleaner separation. I'd use `demo-repo` for now and rename/reorganize later if needed -- avoiding premature infrastructure proliferation.

**Cloud Build service account** needs these roles (check and add if missing):
- `roles/run.admin` (deploy to Cloud Run)
- `roles/iam.serviceAccountUser` (act as the Cloud Run service account)
- `roles/cloudsql.client` (connect to Cloud SQL for migrations)

---

## 5. Monthly Cost Estimate (Phase 1 Steady-State)

| Service | Tier / Usage | Monthly Cost |
|---------|-------------|-------------|
| Cloud SQL (PostgreSQL) | db-g1-small, 10GB SSD, us-central1 | ~$26 |
| Cloud Run | Low traffic, scale-to-zero, well within free tier (2M requests/mo, 360K vCPU-sec) | $0 |
| Artifact Registry | Single image, multiple tags, well within free tier (500MB) | $0 |
| Cloud Build | Occasional builds on push to main, well within free tier (120 build-min/day) | $0 |
| Cloud SQL backups | Automated daily, 7-day retention, ~1GB | ~$0.10 |
| Vertex AI embeddings | Not used until Wave 2. When used: negligible at this volume. | $0 |
| Secret Manager | 1-3 secrets, <10K access operations/mo | $0 (free tier: 6 active secret versions) |
| **Total** | | **~$26/mo** |

**What's NOT included (deferred to later waves/phases):**
- Load Balancer (~$18-20/mo) -- not needed until Wave 4 (console)
- VPC connector (~$6-7/mo) -- not recommended for Phase 1
- Custom domain / SSL certificate -- not needed for Phase 1 internal use
- Cloud DNS zone for TeamForge -- not needed until public-facing

**Comparison with db-f1-micro:** Drops total to ~$7-9/mo. My position: the $17/mo savings is not worth the connection limit risk. But if the sponsor wants the absolute minimum and you accept the constraint (Cloud Run max-instances=2, reduced pool size), it works.

**Cost trajectory:**
- Wave 2 (embeddings): adds ~$0.03-0.05/mo. Negligible.
- Wave 4 (console + LB): adds ~$18-20/mo. Total goes to ~$45/mo.
- If traffic grows beyond free tier: Cloud Run charges are ~$0.40/million requests + vCPU/memory time. You'd need significant traffic to exceed free tier.

---

## Summary of Immediate Actions

Before any infrastructure provisioning, these APIs need enabling:

```bash
# Required for Wave 1
gcloud services enable sqladmin.googleapis.com --project=deckhouse-489723

# Enable now, use in Wave 2 (free to enable)
gcloud services enable aiplatform.googleapis.com --project=deckhouse-489723
```

And verify Cloud Build service account permissions:

```bash
# Get the Cloud Build service account
PROJECT_NUMBER=$(gcloud projects describe deckhouse-489723 --format='value(projectNumber)')
CB_SA="${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com"

# Grant required roles
gcloud projects add-iam-policy-binding deckhouse-489723 \
  --member="serviceAccount:${CB_SA}" --role="roles/run.admin"
gcloud projects add-iam-policy-binding deckhouse-489723 \
  --member="serviceAccount:${CB_SA}" --role="roles/iam.serviceAccountUser"
gcloud projects add-iam-policy-binding deckhouse-489723 \
  --member="serviceAccount:${CB_SA}" --role="roles/cloudsql.client"
```

Let me know if you want me to execute any of these, or if you want to discuss any of the recommendations before locking them in.

---

*Cloud Architect, Hands-On Analytics*
