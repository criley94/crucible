# TeamForge (Crucible) -- Codebase Reference

**Generated:** 2026-03-16
**Repository:** /home/cheston_riley/workspace/crucible
**Branch:** main
**Last commit:** 4d92eb3 -- Wave 3.5: Experience migration, team provisioning, and CLAUDE.md bootstrap

---

## 1. Project Structure

```
crucible/
├── CLAUDE.md                    # Main agent bootstrap (Dante/TL loads from TeamForge API)
├── TEAMFORGE_SPEC.md            # Original project vision document
├── seed.md                      # Seed agent definition (Claude Code agent frontmatter + provisioning logic)
├── cloudbuild.yaml              # GCP Cloud Build CI/CD pipeline
├── docker-compose.yml           # Local dev: PostgreSQL (pgvector/pg16) + API
├── .team_config                 # Symlink config: points to ~/workspace/ai-teams/teams/nautilus
├── .gitignore
├── nautilus_bootstrap_v4.md     # Historical bootstrap document (167KB, legacy reference)
│
├── api/                         # Flask API application
│   ├── Dockerfile               # Python 3.12-slim, gunicorn on port 8080
│   ├── wsgi.py                  # WSGI entry point (create_app)
│   ├── alembic.ini              # Alembic configuration
│   ├── requirements.txt         # Python dependencies
│   ├── seed.py                  # Database seed script (Nautilus team migration from markdown)
│   ├── .env.example             # Environment variable template
│   ├── app/
│   │   ├── __init__.py
│   │   ├── create_app.py        # Flask factory, blueprint registration, error handlers
│   │   ├── config.py            # Config and TestConfig classes
│   │   ├── database.py          # SQLAlchemy engine, session, Base, init_engine()
│   │   ├── middleware/
│   │   │   ├── __init__.py
│   │   │   └── auth.py          # API key auth decorator (require_api_key)
│   │   ├── models/
│   │   │   ├── __init__.py      # Re-exports all models
│   │   │   ├── organization.py  # Organization, EvaluationDimension, OrgSuggestedNorm
│   │   │   ├── team.py          # Team, TeamNorm
│   │   │   ├── agent.py         # Agent, AgentScore
│   │   │   ├── project.py       # ProjectReference, TeamProjectConnection
│   │   │   ├── experience.py    # ExperienceEntry, ReviewEntry
│   │   │   ├── api_key.py       # ApiKey, generate_api_key()
│   │   │   └── helpers.py       # resolve_id_or_slug() utility
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── health.py        # GET /api/v1/health (no auth)
│   │   │   ├── orgs.py          # Org + dimension CRUD
│   │   │   ├── teams.py         # Team CRUD + composition + project connections
│   │   │   ├── agents.py        # Agent CRUD + activate/deactivate
│   │   │   ├── projects.py      # Project reference CRUD
│   │   │   └── experience.py    # Experience write, batch, search, get, list
│   │   └── services/
│   │       ├── __init__.py
│   │       └── embedding.py     # Vertex AI text-embedding-005 wrapper (768-dim)
│   ├── migrations/
│   │   ├── env.py               # Alembic env (reads DATABASE_URL)
│   │   ├── script.py.mako
│   │   └── versions/
│   │       ├── 001_initial_schema.py      # All tables, pgvector extension, vector columns
│   │       ├── 002_widen_agent_type.py    # agent_type String(20) -> String(30)
│   │       └── 003_experience_entries_wave2.py  # title, tags, scope, source_ref, HNSW index
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── conftest.py          # Session-scoped DB, auto-truncate, seed_org fixture
│   │   ├── test_health.py       # 1 test
│   │   ├── test_auth.py         # 3 tests
│   │   ├── test_agents.py       # 8 tests
│   │   ├── test_orgs.py         # 5 tests
│   │   ├── test_teams.py        # 9 tests
│   │   ├── test_projects.py     # 4 tests
│   │   └── test_experience.py   # 14 tests (including privacy boundary + Green Cheese)
│   └── venv/                    # Local virtualenv (not committed)
│
├── scripts/
│   ├── install_seed.sh          # Installs seed.md + provision scripts to ~/.config/teamforge/
│   ├── provision_team.sh        # Shell wrapper for provision_team.py
│   ├── provision_team.py        # Generates CLAUDE.md + .claude/agents/ from TeamForge API
│   └── migrate_experience.py    # Migrates markdown experience files to TeamForge DB
│
├── infrastructure/              # Empty directory (placeholder)
│
├── openspec/
│   ├── specs/                   # Empty (no standalone specs yet)
│   └── changes/                 # Change proposals tracked by OpenSpec
│       ├── wave1-foundation/
│       ├── wave2-experience/
│       ├── wave3-claude-code/
│       ├── experience-migration/
│       ├── team-provisioning/
│       └── api-security-notes/
│
├── project/
│   ├── daily/
│   │   └── 2026-03-15.md
│   ├── knowledge/
│   │   ├── architecture.md      # Stub ("To be populated")
│   │   ├── glossary.md
│   │   ├── mission.md
│   │   ├── risks.md
│   │   ├── runbook.md           # Stub ("To be populated")
│   │   └── vision.md
│   └── planning/
│       ├── backlog.md
│       ├── intake.md
│       ├── product_roadmap.md
│       ├── requirements_direction.md
│       ├── sprint_board.md
│       └── sprint_retrospectives/
│           └── index.md
│
├── .claude/
│   ├── settings.local.json      # Permissions: Bash(*), Read(*), Write(*), etc.
│   ├── agents/                  # Claude Code agent definitions
│   │   ├── dante-tl.md          # Tech Lead (primary/hub agent)
│   │   ├── maya-ra.md           # Requirements Architect
│   │   ├── lena-ux.md           # UX Designer
│   │   ├── nadia-pm.md          # Project Manager
│   │   ├── chris-dev.md         # Backend Developer
│   │   ├── sofia-dev.md         # Frontend Developer
│   │   ├── frank-qa.md          # QA Engineer
│   │   ├── quinn-historian.md   # Historian
│   │   ├── james-po.md          # Product Owner
│   │   └── codebase-analyst.md  # Utility agent (this role)
│   ├── commands/opsx/           # OpenSpec slash commands
│   │   ├── explore.md
│   │   ├── propose.md
│   │   ├── apply.md
│   │   └── archive.md
│   ├── skills/                  # OpenSpec skills
│   │   ├── openspec-explore/SKILL.md
│   │   ├── openspec-propose/SKILL.md
│   │   ├── openspec-apply-change/SKILL.md
│   │   └── openspec-archive-change/SKILL.md
│   └── projects/
│       └── -home-cheston-riley-workspace-crucible/
│           └── memory/
│               └── feedback_dante_direct.md
│
└── ai_team -> ~/workspace/ai-teams/teams/nautilus  # Symlink to team identity files
```

---

## 2. API Endpoints

All endpoints except health require the `X-API-Key` header. Auth resolves the key to an `org_id` via SHA-256 hash lookup, stored in Flask `g.org_id`. All entity queries are scoped to the authenticated org.

### Health

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/health` | None | Returns status, database connectivity, timestamp |

### Organizations

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/v1/orgs` | API key | Create org (name, slug, personal_statement) |
| GET | `/api/v1/orgs/<id_or_slug>` | API key | Get org with dimensions and suggested norms |
| PATCH | `/api/v1/orgs/<id_or_slug>` | API key | Update org name or personal_statement |

### Evaluation Dimensions

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/v1/orgs/<org>/dimensions` | API key | Create dimension |
| GET | `/api/v1/orgs/<org>/dimensions` | API key | List dimensions (sorted by sort_order) |
| PATCH | `/api/v1/orgs/<org>/dimensions/<id>` | API key | Update dimension |
| DELETE | `/api/v1/orgs/<org>/dimensions/<id>` | API key | Delete (409 if scores reference it) |

### Teams

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/v1/teams` | API key | Create team |
| GET | `/api/v1/teams/<id_or_slug>` | API key | Get with roster, norms, active_projects |
| PATCH | `/api/v1/teams/<id_or_slug>` | API key | Update name/description |
| GET | `/api/v1/teams` | API key | List (paginated, ?include_inactive) |
| PATCH | `/api/v1/teams/<id_or_slug>/deactivate` | API key | Deactivate (409 if active members) |
| PATCH | `/api/v1/teams/<id_or_slug>/activate` | API key | Reactivate |

### Team Composition

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/v1/teams/<team>/members` | API key | Add agent to team (422 if standalone_specialist) |
| DELETE | `/api/v1/teams/<team>/members/<agent>` | API key | Remove agent from team |

### Team-Project Connections

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/v1/teams/<team>/projects` | API key | Connect team to project (409 if duplicate) |
| DELETE | `/api/v1/teams/<team>/projects/<project>` | API key | Disconnect (sets disconnected_at, preserves history) |

### Agents

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/v1/agents` | API key | Create agent (team_member or standalone_specialist) |
| GET | `/api/v1/agents/<id_or_slug>` | API key | Get with current_scores |
| PATCH | `/api/v1/agents/<id_or_slug>` | API key | Update name, persona, responsibilities, understanding, relationships, role |
| GET | `/api/v1/agents` | API key | List (paginated, ?team_id, ?unassigned, ?agent_type, ?include_inactive) |
| PATCH | `/api/v1/agents/<id_or_slug>/deactivate` | API key | Set status=inactive |
| PATCH | `/api/v1/agents/<id_or_slug>/activate` | API key | Set status=active |

**Note:** There is no DELETE endpoint for agents. Agents are deactivated, never deleted ("SOULs are sacred").

### Projects

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/v1/projects` | API key | Create project reference |
| GET | `/api/v1/projects/<id_or_slug>` | API key | Get with connected_teams |
| PATCH | `/api/v1/projects/<id_or_slug>` | API key | Update name/description |
| GET | `/api/v1/projects` | API key | List (paginated) |
| DELETE | `/api/v1/projects/<id_or_slug>` | API key | Delete (409 if active team connections) |

### Experience

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/v1/experience` | API key | Create single entry (generates embedding via Vertex AI) |
| POST | `/api/v1/experience/batch` | API key | Create up to 50 entries atomically |
| POST | `/api/v1/experience/search` | API key | Semantic vector search with privacy boundaries |
| GET | `/api/v1/experience/<id>` | API key | Get single entry by UUID |
| GET | `/api/v1/agents/<agent_id>/experience` | API key | List entries by agent (paginated, filterable) |

**Search privacy rules:**
- An agent always sees their own entries (any scope)
- An agent sees `scope=team` entries only if they share the same `team_id`
- An agent sees `scope=org` entries from any agent in the org
- An agent NEVER sees another agent's `scope=agent` (personal) entries

**Search filters:** observation_types, project_ref_id, scope, tags (array overlap), created_after, created_before

---

## 3. Data Model

### Tables (12 total)

**organizations**
- `id` UUID PK, `name` VARCHAR(255), `slug` VARCHAR(100) UNIQUE, `personal_statement` TEXT, `created_at`, `updated_at`

**evaluation_dimensions**
- `id` UUID PK, `org_id` FK->organizations, `name` VARCHAR(100), `description` TEXT, `sort_order` INT, `created_at`, `updated_at`
- Unique: (org_id, name)

**teams**
- `id` UUID PK, `org_id` FK->organizations, `name` VARCHAR(255), `slug` VARCHAR(100), `description` TEXT, `status` VARCHAR(20) default 'active', `created_at`, `updated_at`
- Unique: (org_id, slug)

**team_norms**
- `id` UUID PK, `team_id` FK->teams, `title` VARCHAR(255), `body` TEXT, `status` VARCHAR(20) default 'active', `promoted_to_org` BOOLEAN default false, `created_at`, `updated_at`

**org_suggested_norms**
- `id` UUID PK, `org_id` FK->organizations, `source_team_id` FK->teams (nullable), `title` VARCHAR(255), `body` TEXT, `created_at`, `updated_at`

**agents**
- `id` UUID PK, `org_id` FK->organizations, `team_id` FK->teams (nullable), `name` VARCHAR(255), `slug` VARCHAR(100), `agent_type` VARCHAR(30), `role` VARCHAR(100), `persona` TEXT, `responsibilities` TEXT, `understanding` TEXT (nullable), `relationships` TEXT (nullable), `status` VARCHAR(20) default 'active', `created_at`, `updated_at`
- Unique: (org_id, slug)
- agent_type values: "team_member", "standalone_specialist"

**agent_scores**
- `id` UUID PK, `agent_id` FK->agents, `dimension_id` FK->evaluation_dimensions, `current_score` NUMERIC(3,1), `rolling_average` NUMERIC(3,1), `review_count` INT default 0, `last_reviewed_at` TIMESTAMP, `updated_at`
- Unique: (agent_id, dimension_id)

**project_references**
- `id` UUID PK, `org_id` FK->organizations, `name` VARCHAR(255), `slug` VARCHAR(100), `description` TEXT, `created_at`, `updated_at`
- Unique: (org_id, slug)

**team_project_connections**
- `id` UUID PK, `team_id` FK->teams, `project_id` FK->project_references, `connected_at` TIMESTAMP, `disconnected_at` TIMESTAMP (nullable)
- Soft-disconnect pattern: disconnected_at is set rather than row deleted

**experience_entries**
- `id` UUID PK, `org_id` FK->organizations, `agent_id` FK->agents, `team_id` FK->teams (nullable), `project_ref_id` FK->project_references (nullable), `observation_type` VARCHAR(50), `title` VARCHAR(255) (nullable), `body` TEXT, `tags` VARCHAR(100)[], `scope` VARCHAR(20) default 'agent', `source_ref` VARCHAR(255) (nullable), `embedding` vector(768), `created_at`
- HNSW index on embedding (vector_cosine_ops, m=16, ef_construction=64)
- Valid observation_types: lesson, pattern, process_gap, heuristic, relationship_note, decision, observation, recall
- Valid scopes: agent, team, org

**review_entries**
- `id` UUID PK, `org_id` FK->organizations, `subject_agent_id` FK->agents, `reviewer_agent_id` FK->agents (nullable), `reviewer_type` VARCHAR(20), `project_ref_id` FK->project_references (nullable), `scores` JSONB, `narrative` TEXT, `narrative_embedding` vector(768), `created_at`
- **Note:** No API endpoints exist for review_entries yet. Schema is defined (Wave 1 placeholder) but no routes serve it.

**api_keys**
- `id` UUID PK, `org_id` FK->organizations, `key_hash` VARCHAR(255) UNIQUE, `key_prefix` VARCHAR(8), `name` VARCHAR(255), `is_active` BOOLEAN default true, `created_at`, `last_used_at`
- Keys are SHA-256 hashed. Raw key never stored server-side.
- Key format: `tf_` prefix + 32-byte hex token

### Key Relationships

```
Organization 1---* Team
Organization 1---* Agent
Organization 1---* EvaluationDimension
Organization 1---* OrgSuggestedNorm
Organization 1---* ApiKey
Organization 1---* ProjectReference
Team 1---* Agent
Team 1---* TeamNorm
Team *---* ProjectReference (via TeamProjectConnection)
Agent 1---* AgentScore
AgentScore *---1 EvaluationDimension
Agent 1---* ExperienceEntry
```

### Indexes

- `ix_organizations_slug` on organizations(slug)
- `ix_teams_org_slug` on teams(org_id, slug)
- `ix_agents_org_slug` on agents(org_id, slug)
- `ix_agents_org_team` on agents(org_id, team_id)
- `ix_agents_org_type` on agents(org_id, agent_type)
- `ix_agent_scores_agent` on agent_scores(agent_id)
- `ix_team_project_active` on team_project_connections(team_id, disconnected_at)
- `ix_experience_agent`, `ix_experience_team`, `ix_experience_project` on experience_entries
- `ix_experience_entries_observation_type`, `ix_experience_entries_scope`, `ix_experience_entries_created_at`
- `ix_experience_entries_org_agent`, `ix_experience_entries_org_team` (compound)
- `ix_experience_entries_embedding` HNSW vector index
- `ix_review_subject`, `ix_review_reviewer` on review_entries

---

## 4. Infrastructure

### GCP Project
- **Project ID:** `deckhouse-489723`
- **Region:** `us-central1`

### Cloud Run
- **Service name:** `teamforge-api`
- **Image:** `us-central1-docker.pkg.dev/deckhouse-489723/demo-repo/teamforge-api`
- **Port:** 8080
- **Memory:** 512Mi
- **Min instances:** 0 (scale to zero)
- **Max instances:** 3
- **Auth:** `--allow-unauthenticated` (API key auth is application-level, not IAM)
- **UAT URL:** `https://teamforge-api-1019921786449.us-central1.run.app`

### Cloud SQL
- PostgreSQL with pgvector extension enabled
- Shared infrastructure (used by multiple projects, not locked to TeamForge)
- Cost: ~$26/mo for the instance (org-wide)
- Connection via DATABASE_URL environment variable

### Vertex AI
- **Model:** `text-embedding-005` (768 dimensions)
- **SDK:** `google-cloud-aiplatform==1.74.0`
- **Usage:** Embedding generation for experience entries on write, and query embedding on search
- Lazy-loaded client in `app/services/embedding.py`

### Cloud Build (CI/CD)
- Trigger: push to main
- Steps: Docker build -> push to Artifact Registry -> deploy to Cloud Run
- Logging: CLOUD_LOGGING_ONLY

### Artifact Registry
- Repository: `demo-repo` in `us-central1`
- Tags: `$COMMIT_SHA` and `latest`

### Local Development
- `docker-compose.yml`: pgvector/pgvector:pg16 + API container
- Default credentials: `teamforge:teamforge@localhost:5432/teamforge`
- Test database: `teamforge_test` (created/dropped by test fixtures)

---

## 5. Scripts and Tooling

### `api/seed.py`
Seeds the production database with Nautilus team data. Reads agent identity files from `~/workspace/ai-teams/teams/nautilus/`. Creates: Hands-On Analytics org, 8 evaluation dimensions, Nautilus team, 9 team agents (Dante, Maya, Lena, Nadia, Chris, Sofia, Frank, Quinn, James), Cloud Architect specialist, 2 project references (Bookmark Manager, Crucible), API key. Idempotent -- skips if org already exists.

### `scripts/migrate_experience.py`
Migrates experience data from markdown files (`~/workspace/ai-teams/teams/nautilus/experience/`) into the TeamForge database via the batch API endpoint. Parses 7 source files (lessons_learned.md, successful_patterns.md, prior_failures.md, team_heuristics.md, relationship_history.md, staging.md, bookmark-manager-retro.md). Maps "Captured by" attribution to agent UUIDs. Idempotent via title-based dedup. Includes count validation and semantic search validation. Supports `--dry-run`.

### `scripts/install_seed.sh`
Installs the seed agent and provisioning scripts to `~/.config/teamforge/`. Copies `seed.md`, `provision_team.sh`, and `provision_team.py`. Checks prerequisites (credentials.json, gcloud, claude CLI). Prints usage instructions.

### `scripts/provision_team.sh`
Shell wrapper that invokes `provision_team.py` with optional `--team TEAM_SLUG` argument.

### `scripts/provision_team.py`
Generates project-level TeamForge configuration by querying the API. Creates `CLAUDE.md` (with TL as main agent), `.claude/agents/{slug}.md` for each roster member, and `.claude/settings.local.json`. Reads credentials from `~/.config/teamforge/credentials.json`, authenticates via GCP identity token. Auto-detects Tech Lead by role.

### Alembic Migrations
Run from `api/` directory:
```
cd api && alembic upgrade head
```
Env reads `DATABASE_URL` from environment, falling back to localhost default.

---

## 6. OpenSpec Changes

| Change | Status | Key Files | Summary |
|--------|--------|-----------|---------|
| `wave1-foundation` | **Complete** (no .openspec.yaml = pre-OpenSpec) | proposal.md, design.md, 3 specs, tasks.md, uat-cases.md, uat-results.md | Three-layer data model, CRUD API, Cloud Run + Cloud SQL, auth. 35/35 UAT pass. |
| `wave2-experience` | **Complete** (no .openspec.yaml = pre-OpenSpec) | proposal.md, design.md, 1 spec, tasks.md | Experience capture, batch write, semantic search with privacy boundaries, Vertex AI embeddings. |
| `wave3-claude-code` | **Complete** (no .openspec.yaml = pre-OpenSpec) | proposal.md, 1 spec | CLAUDE.md bootstrap pattern, agent definition files, experience protocol in bootstrap. |
| `experience-migration` | **Complete** (all tasks checked) | .openspec.yaml, proposal.md, design.md, 1 spec, tasks.md | Migration script for markdown experience -> DB. All 13 tasks done. |
| `team-provisioning` | **Nearly complete** (12/13 tasks checked) | .openspec.yaml, proposal.md, design.md, 2 specs, tasks.md | Seed agent, install script, provision script. Task 3.4 (TL bootstrap verification) unchecked. |
| `api-security-notes` | **Documentation only** | .openspec.yaml, proposal.md | Documents current security posture, known gaps, future hardening. |

**Note:** wave1, wave2, and wave3 changes predate the OpenSpec system and lack `.openspec.yaml` files. The experience-migration, team-provisioning, and api-security-notes changes were created within the OpenSpec framework.

---

## 7. Agent Integration

### Bootstrap Pattern (CLAUDE.md)

Every Claude Code session starts by reading `CLAUDE.md`, which instructs the LLM to:

1. Read credentials from `~/.config/teamforge/credentials.json` (contains api_url, api_key, org_slug, team_slug)
2. Get a GCP identity token via `gcloud auth print-identity-token`
3. Load agent identity from `GET /api/v1/agents/<slug>`
4. Load team context from `GET /api/v1/teams/<team_slug>`
5. Load org context from `GET /api/v1/orgs/<org_slug>`
6. Confirm identity loaded

The main session agent is always the Tech Lead (Dante). Sub-agents are dispatched through the TL using the Agent tool.

### Agent Definition Files (.claude/agents/)

Each file has YAML frontmatter (name, description, model: inherit, permissionMode: default) followed by the same bootstrap sequence. 10 agents defined:
- **dante-tl** -- Tech Lead and hub (primary session agent)
- **maya-ra** -- Requirements Architect (spec discipline)
- **lena-ux** -- UX Designer
- **nadia-pm** -- Project Manager
- **chris-dev** -- Backend Developer
- **sofia-dev** -- Frontend Developer
- **frank-qa** -- QA Engineer
- **quinn-historian** -- Historian
- **james-po** -- Product Owner
- **codebase-analyst** -- Utility agent for repository analysis

### Seed Agent (seed.md)

Global agent file intended for `~/.config/teamforge/seed.md`. Its sole purpose is provisioning: it reads the team roster from the API, generates CLAUDE.md and agent files, then exits. It is not a working agent -- it is a one-time setup tool.

### Experience Protocol

Embedded in CLAUDE.md and all agent definitions. Two operations:
- **Query:** `POST /api/v1/experience/search` with agent_id and team_id in filters. Triggered by decision-making, sponsor questions about history, or familiar patterns.
- **Capture:** `POST /api/v1/experience` with observation_type, body, scope, and team_id. Written proactively during sessions (not deferred to session close).

### Credentials File

Expected at `~/.config/teamforge/credentials.json`:
```json
{
  "api_url": "https://teamforge-api-....run.app",
  "api_key": "tf_...",
  "org_slug": "hands-on-analytics",
  "team_slug": "nautilus"
}
```

---

## 8. Test Coverage

### Test Infrastructure
- **Framework:** pytest with real PostgreSQL (no mocking)
- **Test database:** `teamforge_test` (created/dropped per session via `conftest.py`)
- **Fixtures:** `db_engine` (session-scoped), `clean_tables` (auto, truncates between tests), `app`, `client`, `seed_org`, `auth_header`, `org`
- **Embedding mocks:** Experience tests mock `embed_text` and `embed_texts` with deterministic SHA-256-based fake embeddings

### Test Files and Coverage

| File | Tests | Covers |
|------|-------|--------|
| `test_health.py` | 1 | Health endpoint returns 200 with DB status |
| `test_auth.py` | 3 | Missing key (401), invalid key (401), valid key (200) |
| `test_agents.py` | 8 | Create, duplicate slug (409), standalone specialist, specialist+team (422), get by slug, update, deactivate/activate cycle, filter by type, no DELETE (405) |
| `test_orgs.py` | 5 | Create, duplicate slug (409), get, update, create/duplicate/list dimensions |
| `test_teams.py` | 9 | Create, get with roster, add/remove member, specialist rejection (422), deactivate with members (409), deactivate empty, connect/disconnect project, duplicate connection (409) |
| `test_projects.py` | 4 | Create, get, delete (204), delete with connection (409), list paginated |
| `test_experience.py` | 14 | Single create, all fields, validation (missing body, invalid type, invalid scope, invalid agent), batch create, batch atomic rejection, get by ID, not found, list with pagination, filter by type, search requires agent_id, search finds own entries, privacy blocks other agent personal, team-shared visibility, org-shared visibility, all 8 observation types, Green Cheese cross-project test |

**Total: 44 integration tests**

### UAT (Wave 1)
- **35 manual UAT tests** executed by Frank (QA) against the deployed Cloud Run service
- All 35 passed
- Documented in `/home/cheston_riley/workspace/crucible/openspec/changes/wave1-foundation/uat-results.md`

### Notable Test: Green Cheese Test
The "Green Cheese Test" is the canonical memory validation: write "the moon is made of green cheese" as an experience entry in Project A context, then search for it from Project B context without a project filter. Verifies cross-project experience retrieval works. Exists as both an automated integration test and was run manually against production.

---

## 9. Dependencies

From `/home/cheston_riley/workspace/crucible/api/requirements.txt`:

| Package | Version | Purpose |
|---------|---------|---------|
| flask | 3.1.0 | Web framework |
| flask-cors | 5.0.1 | CORS support |
| sqlalchemy | 2.0.36 | ORM and database toolkit |
| psycopg2-binary | 2.9.10 | PostgreSQL driver |
| alembic | 1.14.1 | Database migrations |
| pgvector | 0.3.6 | pgvector Python bindings |
| gunicorn | 23.0.0 | WSGI HTTP server (production) |
| python-dotenv | 1.0.1 | .env file loading |
| google-cloud-aiplatform | 1.74.0 | Vertex AI SDK (embeddings) |

**Not in requirements.txt but used by tests:** pytest, pytest-cov (installed in venv)

---

## 10. Known State

### Deployed to Production (Cloud Run)
- Full Wave 1 API (orgs, teams, agents, projects, dimensions, auth)
- Full Wave 2 API (experience capture, batch, search with embeddings)
- Cloud SQL database with all 3 migrations applied (001, 002, 003)
- Nautilus team seeded (org, team, 10 agents, dimensions, projects, API key)
- Experience data migrated from markdown (lessons, patterns, heuristics, process gaps, relationship notes, staging observations, retrospective)

### Deployed but Not Fully Verified
- Team provisioning task 3.4 (TL bootstrap from API in a fresh project) is unchecked in the task list

### Local Only / Not Deployed
- `infrastructure/` directory is empty (no Terraform/IaC files)
- `project/knowledge/architecture.md` and `project/knowledge/runbook.md` are stubs
- Cloud Build trigger existence is declared in `cloudbuild.yaml` but the trigger configuration in GCP is not tracked in the repo

### Schema vs API Drift
- **review_entries** table exists in the database (created in migration 001) but has NO API endpoints. The ReviewEntry model exists in `app/models/experience.py` but no routes serve it. This is by design -- review endpoints are planned for a future wave.
- **team_norms** and **org_suggested_norms** tables exist but have no dedicated API endpoints. Norms are read-only through the team and org GET endpoints. There are no create/update/delete routes for norms.
- **agent_scores** table exists and scores are returned in the agent GET response, but there are no endpoints to SET scores. Scores are pre-created (all null) during seeding.

### Known Gaps
- No API key rotation or expiration mechanism (documented in api-security-notes)
- No rate limiting
- Cloud Run configured with `--allow-unauthenticated` (application-level auth only, no IAM layer)
- No admin/management endpoints for API key creation (keys created only via seed.py)
- `python-dotenv` is in requirements.txt but never explicitly loaded in application code (not needed in production since env vars are set by Cloud Run)
- The `ai_team` symlink points to a local path (`~/workspace/ai-teams/teams/nautilus`) that only exists on the developer's machine

### Cost
- Cloud SQL instance: ~$26/mo (shared org-wide, not TeamForge-specific)
- Cloud Run: minimal (scale-to-zero, pay-per-request)
- Vertex AI embeddings: usage-based (text-embedding-005)
- Total ceiling: ~$46/mo ($20/mo max above DB cost per sponsor approval)
