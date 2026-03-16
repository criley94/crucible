# Design: Wave 2 Experience Capture and Retrieval

**Author:** Dante (TL)
**Status:** Approved (sponsor resolved B1-B3 on 2026-03-16)
**Date:** 2026-03-16

---

## Architectural Decisions

### AD11: Embedding Generation — Synchronous

Embeddings are generated synchronously on the write path. When an experience entry is created, the API calls Vertex AI to embed the body text before returning the response.

**Rationale:** Our volume is tiny — the entire Nautilus experience corpus is ~70 entries. A single embedding call takes ~200ms. Even a batch of 20 entries at session close is ~4 seconds. Async adds a task queue, retry logic, and a "not yet searchable" state. Not worth it for Phase 1.

**Tradeoff:** Write latency increases by ~200ms per entry. Acceptable. If batch writes become slow, we can parallelize the Vertex AI calls within the batch handler.

**Fallback:** If Vertex AI is unavailable, the entry is persisted with `embedding = NULL`. It won't appear in vector search but will appear in list endpoints. No retry mechanism in Phase 1.

### AD12: Vector Index — HNSW

**Decision: HNSW (Hierarchical Navigable Small World) index on the embedding column.**

| Option | Build Time | Query Speed | Memory | Best For |
|--------|-----------|-------------|--------|----------|
| IVFFlat | Fast | Good (requires tuning `nprobe`) | Lower | Large datasets (100K+) |
| HNSW | Slower | Excellent (no tuning needed) | Higher | Small-medium datasets |

At our scale (hundreds to low thousands of entries), HNSW is the clear choice. No tuning parameters, consistently good recall. The memory overhead is negligible at our volume.

**Index parameters:** `m=16, ef_construction=64` (pgvector defaults). These are well-suited for our scale.

### AD13: Search Query Embedding — Server-Side

The search endpoint receives a natural language query string. The API embeds the query server-side using the same Vertex AI model and parameters used for entry embeddings. The caller sends text; the system handles embedding.

### AD14: Batch Semantics — Atomic with Parallel Embedding

Batch writes are atomic: if any entry fails validation, none are saved. Embeddings for a batch are generated in parallel (concurrent Vertex AI calls) to minimize latency. If any embedding fails, the entry is saved with `embedding = NULL`.

### AD15: Result Set Limits (B4 resolved)

Default: 10 results. Maximum: 50. The caller specifies via `limit` parameter. This is sufficient for on-demand retrieval — agents need the most relevant few results, not a full corpus dump.

### AD16: No Recency Weighting (B5 resolved)

All experience is equally weighted for Phase 1. Vector similarity alone determines ranking. The `created_at` timestamp is in every response, so callers can apply recency logic client-side if needed. Recency boosting is a future optimization informed by real usage.

### AD17: Privacy Boundary Enforcement

The search endpoint enforces hard privacy boundaries at the database query level:

```sql
WHERE org_id = :caller_org
  AND (
    agent_id = :caller_agent_id
    OR (scope = 'team' AND team_id = :caller_team_id)
    OR (scope = 'org')
  )
```

This is not a filter the caller can override. It's applied before vector similarity search. An agent cannot see another agent's personal entries under any circumstances.

The caller CAN further narrow within their visible set using additional filters (observation_type, project_ref_id, tags, time range).

### AD18: Observation Type Validation — Application-Level

The 8 observation types (lesson, pattern, process_gap, heuristic, relationship_note, decision, observation, recall) are validated in the API route handler, not in the database. This allows adding new types without a schema migration. The valid set is defined as a constant in the codebase.

---

## Schema Migration Plan

Migration 003 adds the 4 new columns to experience_entries:
- `title` VARCHAR(255) NULLABLE
- `tags` VARCHAR(100)[] DEFAULT '{}'
- `scope` VARCHAR(20) NOT NULL DEFAULT 'agent'
- `source_ref` VARCHAR(255) NULLABLE

Plus indexes on: agent_id, team_id, project_ref_id, observation_type, scope, created_at, and HNSW on embedding.

No changes to review_entries (out of scope for Wave 2).

---

## Vertex AI Integration

**Endpoint:** `us-central1-aiplatform.googleapis.com`
**Model:** `text-embedding-005` (latest stable, 768 dimensions)
**Auth:** Application Default Credentials (Cloud Run service account)
**Library:** `google-cloud-aiplatform` Python SDK

The embedding service is a thin wrapper module (`app/services/embedding.py`) that:
1. Takes text input
2. Calls Vertex AI text-embedding
3. Returns a list of 768 floats
4. Returns None on failure (logged, not raised)

This keeps the Vertex AI dependency isolated and mockable for tests.
