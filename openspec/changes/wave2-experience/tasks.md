# Tasks: Wave 2 Experience Capture and Retrieval

**Author:** Dante (TL)
**Date:** 2026-03-16

---

## Phase A: Schema and Model (blocks everything)

### A1: Alembic migration 003 — experience_entries schema update
Add title, tags, scope, source_ref columns. Add indexes. Add HNSW index on embedding column.

### A2: Update ExperienceEntry model
Add new fields to SQLAlchemy model. Update to_dict(). Add VALID_OBSERVATION_TYPES constant.

## Phase B: Embedding Service (blocks search)

### B1: Vertex AI embedding service module
Create `app/services/embedding.py` — thin wrapper for Vertex AI text-embedding API. Returns 768-dim vector or None on failure.

### B2: Add google-cloud-aiplatform to requirements.txt

## Phase C: API Endpoints (blocks testing)

### C1: POST /api/v1/experience — single entry write
Validate input, create entry, generate embedding synchronously, return created entry.

### C2: POST /api/v1/experience/batch — batch write
Atomic batch creation with parallel embedding generation.

### C3: POST /api/v1/experience/search — semantic search
Embed query, apply privacy boundaries + filters, vector similarity search, return ranked results.

### C4: GET /api/v1/experience/{id} — single entry retrieval

### C5: GET /api/v1/agents/{agent_id}/experience — agent experience list
Paginated list with filters by type, scope, project.

## Phase D: Testing

### D1: Integration tests for experience write endpoints
### D2: Integration tests for search with privacy boundaries
### D3: Green Cheese Test (automated)

## Phase E: Deploy and Verify

### E1: Deploy updated API to Cloud Run
### E2: Run Green Cheese Test against production

---

## Dependency Graph

```
A1 → A2 → C1 → C2
              → C3 (also needs B1)
              → C4
              → C5
B1 ← B2
D1 ← C1,C2
D2 ← C3
D3 ← C3
E1 ← all code tasks
E2 ← E1
```
