## Why

The Nautilus team's experience data (24 lessons, 14 patterns, 7 process gaps, 13 heuristics, relationship history, staging observations, and a full retrospective) lives in markdown files at `~/workspace/ai-teams/teams/nautilus/experience/`. The TeamForge API and experience layer (Wave 2) are live in production with vector embeddings and semantic search. Until the markdown data is migrated into the database, agents bootstrapping from the API have no experience to query -- the system works but the knowledge base is empty. This is the final step to make the experience layer functional for real work.

## What Changes

- A Python migration script parses all 7 experience markdown files into individual entries
- Each entry is mapped to the correct `observation_type` (lesson, pattern, process_gap, heuristic, relationship_note, observation)
- Each entry is attributed to the correct `agent_id` based on the "Captured by" field in the markdown
- All entries are scoped as `team` (shared Nautilus team knowledge)
- Entries are POSTed to the production experience API via the batch endpoint (max 50 per batch)
- Vertex AI generates embeddings on write (existing Wave 2 behavior)
- Migration is validated by querying the API and running a semantic search

## Capabilities

### New Capabilities
- `experience-migration-script`: One-time Python migration script that parses Nautilus experience markdown files and loads them into the TeamForge database via the experience API

### Modified Capabilities
None. The experience API is unchanged -- this is a data migration using existing endpoints.

## Impact

- **Data**: ~80 experience entries will be created in the production database with vector embeddings
- **API**: No changes -- uses existing `POST /api/v1/experience/batch` endpoint
- **Dependencies**: Requires production API access, GCP identity token, and API key from credentials file
- **Cost**: One-time Vertex AI embedding cost for ~80 entries (negligible)
- **Reversibility**: Entries are immutable once written (by design). Migration should be idempotent -- check for existing entries before inserting
