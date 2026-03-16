# Proposal: Wave 2 -- Experience Capture and Retrieval

**Author:** Maya (RA)
**Date:** 2026-03-16
**Status:** Complete -- all capabilities delivered and deployed
**Parent:** TeamForge Phase 1

---

## Problem Statement

TeamForge Wave 1 deployed a persistent identity database for agents, teams, and orgs. But identity without memory is static. The sponsor's thesis is that agents should learn across projects -- observations from Project A should be retrievable during Project B. Today, experience lives in markdown files on disk (staging.md, lessons_learned.md, successful_patterns.md, prior_failures.md, team_heuristics.md, relationship_history.md). These files are loaded in full at every agent spin-up, consuming context window space regardless of relevance. There is no structured retrieval, no cross-project filtering, and no vector search.

Wave 2 makes TeamForge a memory system. Agents write experience to the database at session close. Agents query experience on-demand when they need it. The system returns relevant results ranked by semantic similarity, scoped by structured filters. Experience persists across projects, across sessions, and across time.

The anchor acceptance test (the "Green Cheese Test"): Tell an agent "remember this: the moon is made of green cheese" in Project A. Close the session. Spin up on Project B. Ask the agent to recall it. If it works, the system works.

---

## Scope

### In Scope

1. **Experience entry data model** -- redesign the placeholder experience_entries table to support the full observation taxonomy derived from the current markdown experience system.

2. **Experience write API** -- endpoints for creating experience entries, including batch writes at session close.

3. **Vector embedding pipeline** -- generate embeddings for experience entry body text using Vertex AI text-embedding (768 dimensions, AD2).

4. **Experience retrieval API** -- semantic search endpoint with vector similarity ranking, scoped by structured metadata filters (agent, team, project, observation type, time range).

5. **Observation type taxonomy** -- a defined set of observation types derived from the current markdown experience categories, with room for extension.

6. **Team-level experience** -- experience that belongs to a team rather than a single agent (e.g., team heuristics, successful patterns that the whole team contributed to).

### Out of Scope

1. **Performance evaluation / review system** -- review_entries, scores, rolling averages, review hierarchy. This is a separate module ("HR department") for a future wave. The review_entries table remains a placeholder.

2. **Claude Code integration** -- the client-side changes that make Claude Code call these APIs instead of reading markdown files. This is Wave 3.

3. **Experience migration tooling** -- automated migration of existing markdown experience files into the database. This is a separate spec (see spec breakdown below) but may be deferred to Wave 3 depending on build timeline.

4. **Relationship dynamics structured model** -- ambiguity A5 remains open. Relationship observations are captured as experience entries with observation_type = 'relationship_note'. A structured pair-relationship model is deferred pending sponsor input.

5. **Management console views** -- Wave 4.

6. **Norm management workflow** -- separate domain, future wave.

---

## Resolved Decisions (Sponsor Confirmed 2026-03-16)

### B1: What triggers experience capture? → RESOLVED: Any time, configurable

Agents can write experience at any time via explicit API call — mid-session or at session close. This is the default behavior. The trigger model is configurable (future teams or orgs could restrict to session-close-only if desired, but the API does not enforce timing constraints).

### B2: Retrieval scoping → RESOLVED: Real-world privacy boundaries

The search enforces real-world privacy:
- An agent sees their OWN entries (all scopes)
- An agent sees TEAM-shared entries (`scope = 'team'`) for their current team
- An agent sees ORG-shared entries (`scope = 'org'`)
- An agent NEVER sees another agent's personal entries (`scope = 'agent'`). Hard boundary.

This is analogous to a real workplace: you see your own notes, your team's shared drive, and company-wide announcements. You don't read other people's private notes.

### B3: Should experience entries be immutable? → RESOLVED: Yes, immutable

Entries are write-once. No UPDATE endpoint. If an observation needs refinement, write a new entry. The Historian's curation workflow becomes "promote by writing a refined entry" rather than "edit in place." Embeddings are generated once and never re-computed.

### B4: What is the maximum result set size for retrieval?

**Context:** Vector similarity search can return the entire corpus ranked by relevance. The caller needs a bounded result set.

**My recommendation:** Default to 10 results, allow the caller to specify up to 50. This is a design-level decision (Dante's call on the default), but the spec needs a stated maximum so the API contract is clear. Flagging for discussion rather than prescribing.

### B5: Is there a concept of experience "expiry" or "staleness"?

**Context:** A lesson learned two years ago may be less relevant than one learned last week. Does the system weight recency, or is all experience equally weighted?

**Options:**
- (a) **No staleness.** All experience is equally weighted. Vector similarity alone determines relevance.
- (b) **Recency boost.** More recent entries get a boost in the ranking. The boost factor is configurable.
- (c) **Explicit expiry.** Entries older than N days are excluded from retrieval unless explicitly requested.

**My recommendation:** Option (a) for Wave 2. Recency boosting (b) is a retrieval quality optimization that should be informed by real usage data. Building it now would be premature. The timestamp is always available in the response, so callers can apply their own recency logic. Flag for Dante as a future optimization.

---

## Non-Blocking Questions (Can Be Resolved During Design)

### NB1: Embedding generation -- synchronous or asynchronous?

When an experience entry is written, should the embedding be generated inline (blocking the response) or in a background job? This is an architectural decision for Dante. The spec requires that the embedding exists before the entry is retrievable via vector search. The timing of generation is design-level.

### NB2: Vector index type (IVFFlat vs. HNSW)?

Already flagged in the Wave 1 spec as Dante's decision. HNSW is generally better for our scale (thousands of entries, not millions), but the tradeoff is Dante's to make.

### NB3: Embedding for the search query -- where does it happen?

The retrieval API receives a natural language query. That query must be embedded before vector comparison. This happens server-side (the API calls Vertex AI to embed the query). This is an implementation detail but worth confirming during design so the API contract is clear about what the caller sends (text) vs. what the system does (embed + search).

---

## Spec Breakdown

### Spec 1: experience-capture (BLOCKING -- write this first)

The core spec. Covers:
- Experience entry data model (redesigned from placeholder)
- Observation type taxonomy
- Write API (single entry + batch)
- Retrieval API (vector similarity search with structured filters)
- Embedding pipeline requirements (what must be true, not how to build it)
- Team-level experience model

This spec supports the Green Cheese Test end-to-end.

### Spec 2: experience-seed-migration (NON-BLOCKING -- can parallel or defer)

Migration of existing Nautilus markdown experience data into the new schema. Covers:
- Mapping from markdown categories to observation_type taxonomy
- Handling of multi-agent entries (team heuristics, relationship history)
- Whether migration is a one-time script or a repeatable process
- Acceptance criteria: the current markdown experience corpus is queryable via the retrieval API

This spec may be deferred to Wave 3 if build timeline is tight. The system works without it -- it just starts with an empty experience corpus.

---

## Dependencies

| Dependency | Status | Impact |
|-----------|--------|--------|
| Wave 1 schema deployed (experience_entries table exists) | DONE | Migration will alter this table if schema changes are needed |
| Vertex AI text-embedding API enabled | DONE (AD10 noted it should be enabled) | Verify actual enablement before build |
| pgvector extension enabled | DONE | Vector columns already exist |
| Wave 1 CRUD API deployed | DONE | Experience write API follows same patterns |

---

## Risks

### R1: Vertex AI embedding latency on write path

If embedding is synchronous, every experience write includes a Vertex AI API call. At session close with a batch of 10-20 entries, this could add noticeable latency. Mitigation: Dante evaluates async vs. sync during design.

### R2: Embedding cost at scale

At ~$0.025/1K queries (AD2), and assuming 50-100 experience entries per project per team, the embedding cost is negligible for Phase 1. But if the system scales to multiple orgs with heavy usage, embedding cost could grow. Not a Wave 2 concern, but worth noting.

### R3: Retrieval quality depends on embedding quality

The Green Cheese Test is a semantic retrieval test. If the embedding model does not capture the semantic relationship between "the moon is made of green cheese" (stored) and "what did I tell you about the moon?" (query), the test will produce a false negative. Mitigation: test early with the actual Vertex AI model and representative queries.

### R4: Placeholder table schema changes require migration

The existing experience_entries table is deployed in production with seed data (none, since it is a placeholder with no write endpoints). Schema changes require an Alembic migration. Low risk since no data exists in the table yet.

---

## Success Criteria

1. An experience entry can be written via the API with structured metadata and free-text body.
2. The free-text body is vector-embedded (768 dimensions, Vertex AI).
3. A natural language query to the retrieval API returns semantically relevant entries ranked by similarity.
4. Retrieval can be filtered by agent_id, team_id, project_ref_id, observation_type, and time range.
5. The Green Cheese Test passes: write an entry in one project context, retrieve it from a different project context via semantic query.
6. Batch writes are supported (multiple entries in one API call).
7. All operations are org-scoped (multi-tenant boundary enforced).

---

## Document Status

B1-B3 resolved by sponsor (2026-03-16). B4-B5 resolved in design (AD15, AD16).
All capabilities implemented and deployed. Green Cheese Test passing (0.7038 similarity).
