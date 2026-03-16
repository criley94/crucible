# Spec: experience-capture

**Parent Proposal:** wave2-experience
**Author:** Maya (RA)
**Status:** Complete -- implemented and deployed. All blocking questions resolved.
**Date:** 2026-03-16

---

## What This Spec Covers

The data model, API endpoints, observation taxonomy, and embedding requirements for writing and retrieving agent experience. This is the core spec for Wave 2 and the primary enabler of the Green Cheese Test.

This spec defines WHAT the system does. Architectural choices (sync vs. async embedding, index types, caching strategies) are Dante's domain.

---

## Data Model

### experience_entries (redesigned from Wave 1 placeholder)

The Wave 1 placeholder table is close to the final shape. The changes below are incremental, not a full redesign.

| Field | Type | Constraints | Notes | Change from Placeholder |
|-------|------|-------------|-------|------------------------|
| id | UUID | PK | System-generated | No change |
| org_id | UUID | FK -> organizations, NOT NULL | Multi-tenant boundary | No change |
| agent_id | UUID | FK -> agents, NOT NULL | Which agent authored this entry | No change |
| team_id | UUID | FK -> teams, NULLABLE | Team context at time of writing. NULL for org-level or unaffiliated entries. | No change |
| project_ref_id | UUID | FK -> project_references, NULLABLE | Project context at time of writing. NULL for project-independent observations. | No change |
| observation_type | VARCHAR(50) | NOT NULL | See taxonomy below | No change (values now defined) |
| title | VARCHAR(255) | NULLABLE | Short summary for display and scanning. Optional. | NEW |
| body | TEXT | NOT NULL | Free-text observation content | No change |
| tags | VARCHAR(100)[] | NULLABLE, DEFAULT '{}' | Array of free-form tags for lightweight categorization. Examples: 'gcp', 'authentication', 'scope-management'. | NEW |
| scope | VARCHAR(20) | NOT NULL, DEFAULT 'agent' | 'agent', 'team', or 'org'. Indicates the intended audience/ownership. | NEW |
| source_ref | VARCHAR(255) | NULLABLE | Optional reference to a source document, session ID, or external context. | NEW |
| embedding | vector(768) | NULLABLE | Vector embedding of body text. NULL until embedding is generated. | No change (dimensions confirmed at 768 per AD2) |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Immutable once set | No change |

**Key design decisions:**

**title (NEW):** The current markdown files use section headers (e.g., "L14: Experience Layer Capture Must Be Decoupled from Curation"). A title field supports scanning and display without reading the full body. Optional because some entries (quick observations, green-cheese-style recall) do not need titles.

**tags (NEW):** The current markdown files do not have tags, but the experience entries are organized by file (lessons_learned, team_heuristics, etc.). Tags provide a more flexible categorization layer. An entry can have multiple tags. Tags are free-form strings, not a managed taxonomy -- the caller defines them. This supports emergent categorization without requiring a tag management system.

**scope (NEW):** Distinguishes between agent-level experience (one agent's observation), team-level experience (shared team knowledge like heuristics), and org-level experience (cross-team knowledge). This field drives retrieval defaults: an agent querying for experience sees their own agent-scoped entries plus team-scoped entries for their current team, plus org-scoped entries. The query can override this default.

**source_ref (NEW):** Provides traceability. When migrating markdown entries, source_ref can reference the original file and entry ID (e.g., "lessons_learned.md#L14"). For entries written by Claude Code sessions, source_ref can reference the session or conversation ID.

**Immutability (RESOLVED -- B3):** Entries are immutable once created (sponsor confirmed). No UPDATE endpoint is provided. If an observation needs refinement, a new entry is created. The embedding is generated once and never re-computed.

---

## Observation Type Taxonomy

Derived from the current markdown experience file categories. Each observation_type maps to one or more current files.

| observation_type | Description | Current Markdown Source |
|-----------------|-------------|----------------------|
| `lesson` | Something the team or agent learned from experience. A reusable insight. | lessons_learned.md (L1-L24) |
| `pattern` | A successful, repeatable approach. Describes what to do, not just what was learned. | successful_patterns.md (P1-P14) |
| `process_gap` | A process gap that produced a suboptimal outcome. Framed as learning per sponsor directive (no "failures"). | prior_failures.md (FL1-FL7) |
| `heuristic` | A rule of thumb for decision-making. Shorter and more prescriptive than a lesson. | team_heuristics.md (H1-H13) |
| `relationship_note` | An observation about how two or more agents (or an agent and the sponsor) work together. Interaction dynamics, trust signals, conflict patterns. | relationship_history.md |
| `decision` | A significant decision and its rationale. Not every decision -- only ones worth retrieving later. | discovery_decisions.md, design.md (AD1-AD10) |
| `observation` | A general observation that does not fit other categories. The catch-all. | staging.md entries before promotion |
| `recall` | Explicitly requested memory storage. "Remember this: X." The type that directly enables the Green Cheese Test. | No current equivalent -- this is new |

**Extensibility:** The observation_type field is a VARCHAR, not an enum. New types can be added without a schema migration. The API should validate against a known set and reject unknown types, but the known set is configurable (not hardcoded in the schema). Dante decides the validation mechanism.

**The `recall` type:** This is the most novel type. It exists specifically for the Green Cheese Test use case -- an agent or the sponsor says "remember this" and the system stores it as a first-class experience entry. It is semantically distinct from a lesson or pattern because it is not an analytical observation; it is a raw memory deposit.

---

## API Endpoints

All endpoints are org-scoped via the existing API key authentication middleware (AD5).

### POST /api/v1/experience

Create a single experience entry.

**Request body:**

```
{
  "agent_id": "uuid",           // REQUIRED - authoring agent
  "team_id": "uuid",            // OPTIONAL - team context
  "project_ref_id": "uuid",     // OPTIONAL - project context
  "observation_type": "string", // REQUIRED - from taxonomy
  "title": "string",            // OPTIONAL
  "body": "string",             // REQUIRED - the observation text
  "tags": ["string"],           // OPTIONAL - free-form tags
  "scope": "string",            // OPTIONAL - defaults to "agent"
  "source_ref": "string"        // OPTIONAL
}
```

**Response:** 201 Created with the full entry (including generated id and created_at). The embedding field is NOT included in the response (it is an internal implementation detail).

**Validation:**
- agent_id must reference an active agent in the authenticated org
- team_id, if provided, must reference a team in the authenticated org
- project_ref_id, if provided, must reference a project in the authenticated org
- observation_type must be in the known taxonomy
- scope must be one of: 'agent', 'team', 'org'
- body must be non-empty

**Embedding generation:** The body text must be embedded before the entry is retrievable via vector search. Whether this happens synchronously (blocking the response) or asynchronously (entry is created immediately, embedding follows) is an architectural decision for Dante. The spec requires: (1) the entry is persisted immediately on write, and (2) the embedding is generated without requiring a separate caller action.

### POST /api/v1/experience/batch

Create multiple experience entries in a single request. This is the primary endpoint for session-close writes.

**Request body:**

```
{
  "entries": [
    {
      // Same shape as single entry above
    },
    ...
  ]
}
```

**Response:** 201 Created with an array of created entries.

**Constraints:**
- Maximum batch size: 50 entries per batch (resolved during implementation, enforced in experience.py route handler). The current Nautilus experience corpus is ~70 entries total across all categories. A single session is unlikely to generate more than 20-30 observations.
- All entries in a batch must belong to the same org (enforced by API key).
- Each entry is validated independently. If any entry fails validation, the entire batch is rejected (atomic). Partial success is not supported -- it creates ambiguity about what was saved.

### POST /api/v1/experience/search

Search for experience entries using natural language query with optional structured filters.

**Request body:**

```
{
  "query": "string",              // REQUIRED - natural language search query
  "filters": {                    // OPTIONAL - all filters are optional
    "agent_id": "uuid",           // Filter to entries by this agent
    "team_id": "uuid",            // Filter to entries in this team context
    "project_ref_id": "uuid",     // Filter to entries in this project context
    "observation_types": ["str"], // Filter to these observation types
    "scope": "string",            // Filter to this scope level
    "tags": ["string"],           // Filter to entries with ANY of these tags
    "created_after": "iso-datetime",  // Time range lower bound
    "created_before": "iso-datetime"  // Time range upper bound
  },
  "limit": 10,                    // OPTIONAL - max results (default 10, max 50)
  "min_similarity": 0.0           // OPTIONAL - minimum similarity threshold (0.0-1.0)
}
```

**Response:**

```
{
  "results": [
    {
      "id": "uuid",
      "agent_id": "uuid",
      "agent_name": "string",       // Denormalized for display
      "team_id": "uuid",
      "project_ref_id": "uuid",
      "observation_type": "string",
      "title": "string",
      "body": "string",
      "tags": ["string"],
      "scope": "string",
      "source_ref": "string",
      "created_at": "iso-datetime",
      "similarity": 0.87            // Cosine similarity score (0.0-1.0)
    },
    ...
  ],
  "total_searched": 142,            // How many entries were in the search space
  "query": "string"                 // Echo the query back for context
}
```

**Search behavior:**
1. The query text is embedded using the same Vertex AI model used for entry embeddings.
2. The embedding is compared against all experience_entries in the org that match the structured filters.
3. Results are ranked by cosine similarity (highest first).
4. Results below min_similarity (if specified) are excluded.
5. The top N results (up to limit) are returned.

**Default retrieval scope (RESOLVED -- B2):** The search enforces real-world privacy boundaries:

1. The agent's own entries (any scope) — you always see your own notes
2. Team-shared entries (`scope = 'team'` where `team_id` matches the agent's current team)
3. Org-shared entries (`scope = 'org'`)

An agent NEVER sees another agent's `scope = 'agent'` entries. This is a hard boundary, not a filter option. The effective WHERE clause:

```
WHERE org_id = :caller_org
  AND (
    agent_id = :caller_agent                          -- my own stuff
    OR (scope = 'team' AND team_id = :caller_team)    -- team shared
    OR (scope = 'org')                                -- org shared
  )
```

This supports the Green Cheese Test (same agent, different project — personal entries follow the agent) and team learning (new members see shared knowledge) without leaking private observations between agents.

**When no query is provided:** The spec does not support filterless listing or metadata-only queries in this endpoint. The search endpoint requires a semantic query. If a future need arises for listing entries by metadata only (e.g., "show me all entries by agent X"), that would be a separate GET endpoint. Flagging for Dante to consider during design.

### GET /api/v1/experience/{id}

Retrieve a single experience entry by ID.

**Response:** The full entry object (same shape as search results, minus the similarity score).

**Use case:** After a search returns results, the caller may want to retrieve the full entry for an ID they stored previously.

### GET /api/v1/agents/{agent_id}/experience

List experience entries authored by a specific agent, ordered by created_at descending.

**Query parameters:**
- observation_type (optional): filter by type
- scope (optional): filter by scope
- project_ref_id (optional): filter by project context
- limit (optional, default 20, max 100): pagination
- offset (optional, default 0): pagination

**Response:** Paginated list of experience entries (no similarity scores -- this is a list endpoint, not a search endpoint).

**Use case:** Display an agent's experience history. Useful for the management console (Wave 4) and for agents reviewing their own past observations.

---

## Team-Level Experience

Some experience belongs to a team, not an individual agent. Examples from the current system:

- team_heuristics.md -- rules of thumb the whole team follows
- successful_patterns.md -- patterns any team member may have contributed to
- relationship_history.md -- dynamics between pairs (involves multiple agents)

**Model:** Team experience uses the same experience_entries table with `scope = 'team'`. The `agent_id` field still records who authored the entry (every entry has an author), but the `scope = 'team'` flag indicates the observation is team-shared knowledge.

**Retrieval behavior:** When an agent searches with `team_id` filter, entries with `scope = 'team'` AND `team_id` matching the filter are included alongside agent-scoped entries. This means an agent querying their team's experience sees both their own observations and team-shared observations.

**Who writes team experience?** Any agent can write a team-scoped entry. In the current system, the Historian (Quinn) curates and promotes entries. In the database system, any agent can write with `scope = 'team'`. Whether curation happens before or after writing is a process decision, not a system constraint.

---

## Embedding Pipeline Requirements

These are the requirements the embedding pipeline must satisfy. How Dante builds it is his decision.

1. **Model:** Vertex AI text-embedding API (`text-embedding-005`), 768 dimensions. Per AD2 and design.md (Vertex AI Integration section).

2. **Input:** The `body` field of the experience entry. Not the title, not the tags, not the metadata. Just the body text.
   - **Rationale:** The body is the semantic content. Embedding the title would add noise (titles are short summaries, not additional information). Tags and metadata are handled by structured filters, not vector similarity.

3. **Timing:** The embedding must be generated without requiring a separate caller action. The caller writes the entry; the system handles embedding. Whether this is synchronous or async is Dante's call, subject to: the entry must be retrievable via vector search within a reasonable window after creation. "Reasonable window" for Phase 1: within 60 seconds of creation. This is generous -- if Dante can do synchronous without latency issues, that is simpler.

4. **Query embedding:** When the search endpoint receives a query, the query text must be embedded with the same model and parameters as the stored entries. Consistency between write-time and query-time embedding is required for meaningful similarity scores.

5. **No re-embedding:** Entries are immutable (pending B3 resolution). Embeddings are generated once and never re-computed. If the embedding model changes in the future, a migration strategy would be needed (not a Wave 2 concern).

6. **Null embedding handling:** If embedding generation fails (Vertex AI unavailable, rate limit, etc.), the entry is still persisted with `embedding = NULL`. The entry will not appear in vector search results but will appear in metadata-based list endpoints. The system should log the failure and provide a mechanism to retry (design-level detail for Dante).

---

## The Green Cheese Test -- Walkthrough

This section traces the anchor UAT case through the spec to verify full support.

**Step 1: Agent writes a recall entry in Project A.**

```
POST /api/v1/experience
{
  "agent_id": "<maya-uuid>",
  "project_ref_id": "<project-a-uuid>",
  "observation_type": "recall",
  "body": "The sponsor told me: the moon is made of green cheese. This will be our UAT memory.",
  "scope": "agent"
}
```

System persists the entry. System generates embedding of the body text.

**Step 2: Session closes. Agent spins up on Project B.**

No experience is loaded at spin-up (per AD6 -- on-demand retrieval). The agent receives identity, scores, team context. Lean.

**Step 3: Agent queries for the memory.**

```
POST /api/v1/experience/search
{
  "query": "What did the sponsor tell me about the moon?",
  "filters": {
    "agent_id": "<maya-uuid>"
  },
  "limit": 5
}
```

System embeds the query. System searches against all experience entries in the org where agent_id matches Maya. The "green cheese" entry surfaces because the semantic similarity between the query and the stored body text is high. No project filter is applied -- the entry from Project A is retrievable from the Project B context.

**Step 4: Agent retrieves the result.**

The response includes the body: "The sponsor told me: the moon is made of green cheese. This will be our UAT memory." The similarity score confirms high relevance. The agent recalls correctly.

**Why this works:** The entry is stored with project_ref_id = Project A, but the search does not filter by project. The vector similarity between the query and the stored body is the retrieval mechanism, not project matching. Cross-project retrieval is the default behavior, not a special case.

---

## Indexing Requirements

Minimum required indexes (Dante may add more based on query patterns):

- experience_entries(org_id) -- multi-tenant filtering
- experience_entries(agent_id) -- agent-scoped queries
- experience_entries(team_id) -- team-scoped queries
- experience_entries(project_ref_id) -- project-scoped queries
- experience_entries(observation_type) -- type filtering
- experience_entries(scope) -- scope filtering
- experience_entries(created_at) -- time-range queries and ordering
- pgvector index on embedding column -- type and parameters are Dante's decision (IVFFlat vs. HNSW, per NB2 in the proposal)

**Compound index recommendation:** (org_id, agent_id) and (org_id, team_id) for the most common retrieval patterns. Dante confirms during design.

---

## What This Spec Does NOT Cover

- Review entries and the performance evaluation system (separate module, future wave)
- Claude Code client integration (Wave 3 -- the caller-side changes to use these APIs)
- Management console views for experience browsing (Wave 4)
- Relationship dynamics structured model (deferred pending A5 -- captured as relationship_note observation type)
- Automated experience summarization or deduplication (future optimization)
- Migration of existing markdown experience data (separate spec: experience-seed-migration)

---

## Acceptance Criteria

1. **Write single entry:** POST to /api/v1/experience with valid payload returns 201 with the created entry including generated id and timestamp.

2. **Write batch:** POST to /api/v1/experience/batch with multiple entries returns 201 with all created entries. Atomic -- if any entry fails validation, none are saved.

3. **Validation enforced:** Entries with invalid agent_id, unknown observation_type, or empty body are rejected with 400/422 and a clear error message.

4. **Embedding generated:** After writing an entry, the embedding field is populated (within the timing requirement). Entries with populated embeddings appear in vector search results.

5. **Semantic search works:** POST to /api/v1/experience/search with a natural language query returns results ranked by cosine similarity. Results are semantically relevant to the query.

6. **Structured filters work:** Search results can be filtered by agent_id, team_id, project_ref_id, observation_type, scope, tags, and time range. Filters narrow the result set correctly.

7. **Green Cheese Test passes:** Write an entry with project_ref_id = Project A. Search without project filter using a semantically related query. The entry is returned.

8. **Team experience accessible:** An agent can search and find team-scoped entries for their team, even if another agent authored them.

9. **Org scoping enforced:** Entries from Org A are never returned in searches authenticated as Org B.

10. **Pagination works:** GET /api/v1/agents/{id}/experience returns paginated results with correct limit/offset behavior.

11. **All observation types supported:** Entries can be created with each of the eight defined observation types.

12. **Null embedding handling:** An entry with embedding = NULL is persisted and appears in list endpoints but does not appear in vector search results.
