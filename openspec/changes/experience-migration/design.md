## Context

The Nautilus team has accumulated experience data across two projects (bookmark manager, TeamForge) stored in 7 markdown files. The TeamForge experience API (Wave 2) is live in production with Vertex AI embeddings and semantic search. The migration bridges the gap between the old storage format and the new system.

Source files at `~/workspace/ai-teams/teams/nautilus/experience/`:
- `lessons_learned.md` -- 24 entries (L1-L24), type: lesson
- `successful_patterns.md` -- 14 entries (P1-P14), type: pattern
- `prior_failures.md` -- 7 entries (FL1-FL7), type: process_gap
- `team_heuristics.md` -- 13 entries (H1-H13), type: heuristic
- `relationship_history.md` -- ~12 dated sections, type: relationship_note
- `staging.md` -- 4 unpromoted entries from TeamForge session, type: observation
- `retros/bookmark-manager-retro.md` -- 1 full retrospective, type: observation

## Goals / Non-Goals

**Goals:**
- Migrate all Nautilus experience data into the TeamForge database
- Preserve attribution (which agent captured each entry)
- Generate vector embeddings for all entries (enables semantic search)
- Make the migration idempotent (safe to re-run)
- Validate migration completeness and search functionality

**Non-Goals:**
- Modifying the experience API
- Migrating non-experience data (identity, standards, etc. -- already in DB)
- Cleaning up or editing the source markdown files
- Building a general-purpose markdown-to-API migration framework

## Decisions

### AD1: Parse Strategy -- Section-Based Splitting
Each markdown file uses `## ` headings to delimit entries. Split on `## ` to extract individual entries. The heading becomes the `title`, the body becomes `body`.

Alternative: Line-by-line regex parsing. Rejected -- fragile, heading-based splitting is simpler and matches the consistent format.

### AD2: Attribution Mapping
Each entry has a "Captured by" or "Source" line identifying the agent. Map these to agent UUIDs from the roster:
- "TL" / "Dante" -> `26405c2b-698f-438e-be7d-1ce2bb99b066`
- "Quinn" / "Historian" -> `c7c57451-e0c2-4f2a-a02d-47e63575400f`
- "Maya" / "RA" -> `47ef9fec-f5fe-4ff4-8644-318cbcbc82c0`
- "Lena" / "UX" -> `9df08aa3-eb0f-444a-86b4-20bebb456dfd`
- "Nadia" / "PM" -> `1266fdea-904c-41a0-be2d-8ed4019c3902`
- "Frank" / "QA" -> `cded34a5-ce40-476b-a3d4-293e9cf92dba`
- "Chris" / "Dev" -> `b59d5ddd-321e-4f29-80ac-bb5ba7212229`

Default to Quinn (Historian) for entries where attribution is ambiguous -- the Historian is the canonical curator.

### AD3: Scope Assignment
All migrated entries are `scope: "team"`. These are shared Nautilus team knowledge, not personal agent observations. The staging entries from the TeamForge session that are agent-attributed observations will also be `team` scope since they were written for team consumption.

### AD4: Idempotency via Title Check
Before inserting, query `GET /api/v1/agents/{agent_id}/experience` and check for existing entries with matching titles. Skip duplicates. This makes the script safe to re-run.

Alternative: Delete-and-reinsert. Rejected -- experience entries are immutable by design (no delete endpoint).

### AD5: Batch Endpoint Usage
Use `POST /api/v1/experience/batch` with max 50 entries per batch. With ~80 entries, this is 2 batches. Each batch is atomic -- all succeed or all fail.

### AD6: Relationship History as Multiple Entries
The relationship history file contains multiple dated sections, each covering several relationship observations. Split each dated section into a separate entry with type `relationship_note`. The section heading (date + context) becomes the title.

### AD7: Retro as Single Entry
The full retrospective is one logical document. Migrate as a single `observation` entry with title "Retrospective: Bookmark Manager Project". The body is the full retro text.

### AD8: Staging -- Unpromoted Entries Only
The staging file has both promoted (already in canonical files) and unpromoted entries. Only migrate the 4 unpromoted entries from the TeamForge session (dated 2026-03-15). The promoted entries are already covered by the canonical file migrations.

## Risks / Trade-offs

- **Embedding cost**: ~80 entries x Vertex AI embedding call. Cost is negligible (pennies) but adds ~30 seconds of API latency for the batch writes.
- **Title matching for idempotency**: If titles were manually edited between runs, duplicates could be created. Acceptable risk for a one-time migration.
- **Large body text**: The retro is ~190 lines. The API accepts it, and the embedding model handles up to 2048 tokens. If truncated, the embedding covers the summary, which is sufficient for search relevance.
- **Rate limiting**: Two batch calls to the production API. No rate limiting is configured, so this is not a concern.

## Migration Plan

1. Run migration script from `~/workspace/crucible/` against production API
2. Script reads credentials from `~/.config/teamforge/credentials.json`
3. Script gets fresh GCP identity token via `gcloud auth print-identity-token`
4. Script parses all 7 files, builds entry list
5. Script checks for existing entries (idempotency)
6. Script POSTs in batches of 50
7. Script validates: count check, then semantic search for "What did the team learn about UX involvement?"
8. If validation fails, report which entries are missing -- manual review, no automated rollback needed
