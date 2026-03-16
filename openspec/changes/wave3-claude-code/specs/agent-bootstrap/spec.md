# Spec: Agent Bootstrap -- Claude Code Integration

**Author:** Maya (RA)
**Date:** 2026-03-16
**Status:** Complete -- implemented and operational. See design.md for resolved decisions.
**Parent Proposal:** Wave 3 -- Claude Code Integration
**Spec ID:** wave3-agent-bootstrap

---

## 1. Overview

This spec defines how Claude Code agent definition files change from markdown-file-readers to API-bootstrapped launchers, how credentials are managed, how identity is loaded at dispatch time, how experience is queried and captured via the API, and how a team is provisioned on a project.

The end state: the `.claude/agents/<name>.md` files become thin launchers. All identity content comes from the TeamForge API at runtime.

---

## 2. Current State (What We Are Replacing)

### Current Agent Definition File Structure

Each agent has a file at `.claude/agents/<name>.md` with this structure:

```
---
name: sofia-dev
description: >
  Use for frontend implementation tasks...
model: inherit
permissionMode: default
skills: openspec
---

## Identity

You are Sofia, the Frontend Developer on this team.

## Context Loading

Before doing any work, read the following files in order:

1. `/ai_team/identity/personal_statement.md`
2. `/ai_team/team/sofia-dev/persona.md`
3. `/ai_team/team/sofia-dev/responsibilities.md`
4. `/ai_team/team/sofia-dev/relationships.md`
5. `/ai_team/team/sofia-dev/understanding.md`
6. `/ai_team/experience/staging.md`
7. `/ai_team/identity/operating_rules.md`
8. `/ai_team/identity/output_format.md`

## Always-Load Set

- `/project/planning/sprint_board.md`
- `/project/daily/` -- today's daily log
- `/ai_team/identity/team_roster.md`

## Operating Model

(Role-specific operating instructions)
```

### What This Means

The agent definition file contains:
1. **YAML frontmatter** -- name, description, model, permissions, skills. This is Claude Code metadata.
2. **Identity stub** -- a one-line identity declaration.
3. **File-reading instructions** -- tells the agent to read 8+ markdown files from disk.
4. **Operating model** -- role-specific behavioral instructions.

The identity content (persona, responsibilities, relationships, understanding) lives in markdown files on disk. The agent definition is a pointer, not a container.

### Problems With This Approach

- Identity is scattered across multiple files in a separate repo.
- No structured retrieval -- everything is loaded in full, consuming context window.
- Experience is loaded as a full file dump, not queried by relevance.
- No persistence across repos -- cloning a new project means copying markdown files.
- No central management -- changing an agent's persona means editing a file on disk.

---

## 3. New Agent Definition File Structure

### Template

Each agent definition file becomes a thin launcher that follows this pattern:

```
---
name: <agent-slug>
description: >
  <One-line description of when to dispatch this agent. Unchanged from current.>
model: inherit
permissionMode: default
skills: openspec
---

## Bootstrap

You are an AI agent managed by TeamForge. Your identity, responsibilities, and
team context are stored in the TeamForge API. You MUST load your identity before
doing any work.

### Step 1: Read Credentials

Read the TeamForge configuration:

- Run: `cat ~/.config/teamforge/credentials.json`
- This file contains: `api_url`, `api_key`, `org_slug`, `team_slug`
- Do NOT display the api_key value in your output.

If the credentials file does not exist or is unreadable, STOP and report:
"TeamForge credentials not found at ~/.config/teamforge/credentials.json.
Cannot bootstrap identity. Please run the TeamForge setup."

### Step 2: Load Your Identity

Call the TeamForge API to load your identity:

- Run: `curl -s -H "X-API-Key: $API_KEY" "$API_URL/api/v1/agents/<agent-slug>"`
- Parse the JSON response. Extract and internalize:
  - `name` -- your display name
  - `role` -- your role on the team
  - `persona` -- your personality, working style, values
  - `responsibilities` -- what you own, your boundaries
  - `relationships` -- how you work with each team member
  - `understanding` -- your understanding of your role and the project
  - `current_scores` -- your performance scores (if any)

If the API returns an error, STOP and report: "TeamForge API error during
identity bootstrap: [error message]. Cannot proceed without identity."

### Step 3: Load Team Context

Call the TeamForge API to load your team context:

- Run: `curl -s -H "X-API-Key: $API_KEY" "$API_URL/api/v1/teams/<team-slug>"`
- Parse the JSON response. Extract:
  - `roster` -- who is on your team (names, roles, slugs)
  - `norms` -- team operating norms
  - `active_projects` -- what projects the team is connected to

### Step 4: Load Org Context

- Run: `curl -s -H "X-API-Key: $API_KEY" "$API_URL/api/v1/orgs/<org-slug>"`
- Extract the `personal_statement` (sponsor values) and any org-level context.

### Step 5: Confirm Bootstrap

After loading, output a brief confirmation:
"[<Name> / <Role>] Identity loaded from TeamForge. Team: <team_name>.
Active project(s): <project_list>. Ready."

You are now that agent. Your persona, responsibilities, relationships, and
understanding define how you behave for the rest of this session.

## Experience Protocol

### Querying Experience (Mid-Session)

When you encounter a problem, decision point, or question where past context
would be valuable, query the experience API:

```
curl -s -X POST \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query": "<your question>", "filters": {"agent_id": "<your-agent-uuid>", "team_id": "<your-team-uuid>"}, "limit": 5}' \
  "$API_URL/api/v1/experience/search"
```

Use this when:
- You are making a decision that might have precedent
- You encounter a pattern you think the team has seen before
- You need to recall something from a previous project
- The sponsor or TL references something that happened before

Do NOT query experience speculatively at bootstrap. Load it on-demand when
you have a specific need.

### Capturing Experience (During and End of Session)

When you make an observation worth preserving -- a lesson learned, a pattern
identified, a process gap discovered, a decision made -- write it to the API:

```
curl -s -X POST \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"agent_id": "<your-agent-uuid>", "observation_type": "<type>", "body": "<observation text>", "scope": "<agent|team|org>", "tags": ["<tag1>", "<tag2>"], "team_id": "<your-team-uuid>"}' \
  "$API_URL/api/v1/experience"
```

Valid observation types: lesson, pattern, process_gap, heuristic,
relationship_note, decision, observation, recall.

Scope guide:
- `agent` -- personal to you (your working notes, your lessons)
- `team` -- relevant to anyone on the team (team patterns, shared learnings)
- `org` -- relevant to anyone in the org (cross-team insights)

Write experience proactively when you have something worth capturing. Do not
wait for session close. If the session ends abruptly, anything not written
is lost.

At the end of a session, if you have accumulated observations that you have
not yet written, batch them:

```
curl -s -X POST \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"entries": [<array of entry objects>]}' \
  "$API_URL/api/v1/experience/batch"
```

## Operating Model

<Role-specific operating instructions -- carried over from the current
agent definition file, unchanged.>
```

### What Changed

| Aspect | Before | After |
|--------|--------|-------|
| Identity source | 8+ markdown files on disk | 3 API calls (agent, team, org) |
| Identity content location | Markdown files in a separate repo | TeamForge database |
| Experience read | Full file dump at spin-up | On-demand semantic search mid-session |
| Experience write | Append to `staging.md` | API POST calls during/after session |
| Credential source | N/A (no API calls) | `~/.config/teamforge/credentials.json` |
| Fallback on failure | N/A | Hard stop with error message |
| Agent definition size | ~40 lines (short) | ~80 lines (medium, mostly instructions) |

### What Did NOT Change

- The YAML frontmatter (name, description, model, permissionMode, skills) is unchanged. This is Claude Code metadata, not identity.
- The Operating Model section at the bottom of each file is unchanged. Role-specific behavioral instructions (e.g., "There is no dedicated PO on this team") are still in the agent definition file. These are operational instructions, not identity.
- The dispatch model is unchanged. The sponsor or TL dispatches agents by name via Claude Code's Agent tool.

---

## 4. Credential Management

### Credential File

Location: `~/.config/teamforge/credentials.json`

Contents:
```json
{
  "api_url": "https://teamforge-api-1019921786449.us-central1.run.app",
  "api_key": "<the org's API key>",
  "org_slug": "nautilus-org",
  "team_slug": "nautilus",
  "default_project_slug": "crucible"
}
```

### Why a File, Not an Environment Variable

- Claude Code agents can reliably read files via bash (`cat`).
- A JSON file allows storing multiple values (URL, key, org, team) without multiple env vars.
- The file is in the user's home directory, not in the repo, so it is never committed to git.
- The `.gitignore` does not need to be updated (the file is outside the repo).

### Security Considerations

- The file is readable only by the user (`chmod 600`).
- The agent definition instructs the agent: "Do NOT display the api_key value in your output."
- The API key is org-scoped. It grants access to one org's data. It does not grant cross-org access.
- The credential file is created once during setup and does not need to be recreated per session.

### Setup

The credential file is created manually by the sponsor (or via a setup script). This is a one-time operation per machine:

```bash
mkdir -p ~/.config/teamforge
cat > ~/.config/teamforge/credentials.json << 'EOF'
{
  "api_url": "https://teamforge-api-1019921786449.us-central1.run.app",
  "api_key": "<your-api-key>",
  "org_slug": "nautilus-org",
  "team_slug": "nautilus",
  "default_project_slug": "crucible"
}
EOF
chmod 600 ~/.config/teamforge/credentials.json
```

---

## 5. Bootstrap Flow (Step by Step)

This is the end-to-end flow from the sponsor's perspective.

### Preconditions

1. The TeamForge API is deployed and reachable.
2. The Nautilus org, team, and all agents are seeded in the database.
3. The credential file exists at `~/.config/teamforge/credentials.json`.
4. The agent definition files (`.claude/agents/*.md`) have been updated to the new format.

### Flow: "Spin up Dante on Crucible"

**Sponsor action:** In VSCode with Claude Code, the sponsor types: "Use the dante-tl agent to start work on the Crucible project."

**What happens:**

1. Claude Code loads `.claude/agents/dante-tl.md` as the agent's instructions.
2. Dante reads `~/.config/teamforge/credentials.json` via bash.
3. Dante calls `GET /api/v1/agents/dante-tl` with the API key.
4. Dante receives his full identity (persona, responsibilities, relationships, understanding, scores) as JSON.
5. Dante calls `GET /api/v1/teams/nautilus` with the API key.
6. Dante receives the team context (roster of 8 agents, norms, active projects) as JSON.
7. Dante calls `GET /api/v1/orgs/nautilus-org` with the API key.
8. Dante receives the org context (personal statement) as JSON.
9. Dante internalizes all of this and outputs:
   "[Dante / Tech Lead] Identity loaded from TeamForge. Team: Nautilus. Active project(s): Crucible. Ready."
10. Dante proceeds with the sponsor's request, behaving according to his database-sourced persona.

### Flow: "Dante dispatches Sofia"

**Dante's action:** Dante uses Claude Code's Agent tool to dispatch `sofia-dev` with a task.

**What happens:**

1. Claude Code loads `.claude/agents/sofia-dev.md` as Sofia's instructions.
2. Sofia reads `~/.config/teamforge/credentials.json` via bash.
3. Sofia calls `GET /api/v1/agents/sofia-dev` with the API key.
4. Sofia receives her identity as JSON.
5. Sofia calls `GET /api/v1/teams/nautilus` for team context.
6. Sofia calls `GET /api/v1/orgs/nautilus-org` for org context.
7. Sofia confirms: "[Sofia / Frontend Developer] Identity loaded from TeamForge. Team: Nautilus. Active project(s): Crucible. Ready."
8. Sofia proceeds with Dante's dispatched task.

### Flow: Mid-Session Experience Query

**Trigger:** Sofia is implementing a feature and encounters a pattern she thinks the team has seen before.

**What happens:**

1. Sofia constructs a natural language query: "frontend component patterns for accessible form validation"
2. Sofia calls `POST /api/v1/experience/search` with her agent_id in the filters.
3. The API returns up to 5 semantically relevant experience entries, ranked by similarity.
4. Sofia reads the results and incorporates relevant lessons into her work.
5. Sofia does NOT display raw API responses to the sponsor unless asked. She synthesizes: "Found 3 relevant past observations about form validation patterns."

### Flow: Session-Close Experience Capture

**Trigger:** The session is ending. Sofia has observations to record.

**What happens:**

1. Sofia composes her observations as experience entries.
2. Sofia calls `POST /api/v1/experience/batch` with her observations.
3. Each entry includes: agent_id, observation_type, body, scope, tags, team_id.
4. The API generates embeddings and stores the entries.
5. Sofia confirms: "Wrote 3 experience entries to TeamForge."

---

## 6. Team Provisioning Flow

### What "Provisioning" Means

Provisioning is the act of setting up a repo so that Claude Code can dispatch TeamForge-managed agents. It involves:

1. Creating or updating `.claude/agents/*.md` files with the new API-bootstrapped format.
2. Ensuring the credential file exists.
3. Ensuring the team and agents exist in the database.

### Phase 1 Approach: Template + Manual Setup

For Phase 1, provisioning is semi-manual:

1. **Database setup** (one-time per team): Create the org, team, and agents via the API. This was done during Wave 1-2 testing and is verified by the nautilus-seed-verification task.

2. **Credential setup** (one-time per machine): Create `~/.config/teamforge/credentials.json` as described in Section 4.

3. **Agent definition files** (one-time per repo): Create or update `.claude/agents/*.md` files. Each file follows the template in Section 3, parameterized only by:
   - The agent slug (in the YAML `name` field and in the API URL)
   - The one-line description (in the YAML `description` field)
   - The operating model section (role-specific instructions)

### Provisioning Script (Convenience, Not Required)

A bash script that generates agent definition files from the database:

```bash
#!/bin/bash
# provision-team.sh -- Generate Claude Code agent definitions from TeamForge
#
# Usage: ./provision-team.sh [--team SLUG] [--output-dir DIR]

TEAM_SLUG="${1:-nautilus}"
OUTPUT_DIR="${2:-.claude/agents}"
CREDS_FILE="$HOME/.config/teamforge/credentials.json"

API_URL=$(jq -r .api_url "$CREDS_FILE")
API_KEY=$(jq -r .api_key "$CREDS_FILE")
ORG_SLUG=$(jq -r .org_slug "$CREDS_FILE")
TEAM_SLUG_FROM_CREDS=$(jq -r .team_slug "$CREDS_FILE")

# Fetch team roster
ROSTER=$(curl -s -H "X-API-Key: $API_KEY" "$API_URL/api/v1/teams/$TEAM_SLUG")

# For each agent in roster, generate an agent definition file
echo "$ROSTER" | jq -r '.roster[] | .slug' | while read SLUG; do
  # Fetch agent details for the description
  AGENT=$(curl -s -H "X-API-Key: $API_KEY" "$API_URL/api/v1/agents/$SLUG")
  ROLE=$(echo "$AGENT" | jq -r '.role')
  NAME=$(echo "$AGENT" | jq -r '.name')

  cat > "$OUTPUT_DIR/$SLUG.md" << AGENT_EOF
---
name: $SLUG
description: >
  $NAME -- $ROLE. Dispatched from TeamForge API.
model: inherit
permissionMode: default
---

## Bootstrap

(Standard bootstrap instructions -- see template in spec Section 3)

AGENT_EOF

  echo "Generated $OUTPUT_DIR/$SLUG.md"
done
```

This script is a convenience tool. It is not required for the integration to work. The sponsor or TL can create the files manually.

---

## 7. Fallback Behavior

### When the API Is Unreachable

If any bootstrap API call fails (network error, 5xx response, timeout):

1. The agent outputs: "TeamForge API is unreachable. Bootstrap failed. I cannot load my identity from the database."
2. The agent does NOT proceed with no identity.
3. The agent does NOT fall back to reading markdown files silently (this would create a confusing split where some sessions use the API and some use files, with no visibility into which).
4. The agent suggests: "Check that the API is running and the credentials file is correct. API URL: [url]."

### Rationale for Hard Stop (No Silent Fallback)

The purpose of Wave 3 is to make the API the source of truth. If the agent silently falls back to markdown files, the sponsor has no way to know that the API-based system is failing. Hard stop makes problems visible. The sponsor can then choose to fix the API issue or manually dispatch with explicit markdown file instructions.

### When the Credential File Is Missing

Same behavior: hard stop with a clear error message explaining what is needed.

### When the Agent Is Not Found in the Database

If `GET /api/v1/agents/<slug>` returns 404:

The agent outputs: "Agent '<slug>' not found in TeamForge database. This agent has not been provisioned. Check that the team seed data is complete."

---

## 8. Data Flow Diagram

```
Sponsor in VSCode
       |
       | "Use dante-tl agent for Project X"
       v
Claude Code loads .claude/agents/dante-tl.md
       |
       | (Agent definition says: bootstrap from API)
       v
Agent reads ~/.config/teamforge/credentials.json
       |
       | (Gets: api_url, api_key, org_slug, team_slug)
       v
GET /api/v1/agents/dante-tl         --> Agent identity (persona, responsibilities, etc.)
GET /api/v1/teams/nautilus           --> Team context (roster, norms, projects)
GET /api/v1/orgs/nautilus-org        --> Org context (personal statement)
       |
       | Agent internalizes identity, confirms bootstrap
       v
Agent operates as Dante with full identity
       |
       |--- Mid-session: POST /api/v1/experience/search  (query past context)
       |--- Mid-session: POST /api/v1/experience          (capture observation)
       |--- End-session: POST /api/v1/experience/batch    (capture remaining observations)
       |
       |--- Dispatches sofia-dev via Agent tool
       |         |
       |         v
       |    Sofia bootstraps the same way (reads creds, calls API, loads identity)
       |         |
       |         v
       |    Sofia operates, queries experience, captures experience
       |
       v
Session ends. All experience written to TeamForge API.
```

---

## 9. Agent Definition File Inventory

These files need to be created or updated in `.claude/agents/`:

| File | Agent Slug | Role | Notes |
|------|-----------|------|-------|
| `dante-tl.md` | dante-tl | Tech Lead | Primary dispatch target. Spawns all subagents. |
| `maya-ra.md` | maya-ra | Requirements Architect | Spec authoring. |
| `sofia-dev.md` | sofia-dev | Frontend Developer | Frontend implementation. |
| `chris-dev.md` | chris-dev | Backend Developer | Backend implementation. |
| `frank-qa.md` | frank-qa | QA | Test writing and UAT. |
| `nadia-pm.md` | nadia-pm | Project Manager | Sprint planning. |
| `lena-ux.md` | lena-ux | UX Designer | UX design (Wave 4+). |
| `quinn-historian.md` | quinn-historian | Historian | Experience curation. |

Each file follows the template in Section 3. The only differences between files are:
- The `name` field in YAML frontmatter (the agent slug).
- The `description` field in YAML frontmatter (when to dispatch this agent).
- The agent slug in the `GET /api/v1/agents/<slug>` URL.
- The Operating Model section at the bottom (role-specific behavioral instructions).

The James (PO) agent is excluded. Per the operating model, there is no dedicated PO on this team. The TL handles operational PO responsibilities.

---

## 10. API Endpoints Used (No New Endpoints Required)

All endpoints already exist from Waves 1-2.

| Endpoint | Method | Purpose in Bootstrap |
|----------|--------|---------------------|
| `/api/v1/agents/<slug>` | GET | Load agent identity |
| `/api/v1/teams/<slug>` | GET | Load team context (roster, norms, projects) |
| `/api/v1/orgs/<slug>` | GET | Load org context (personal statement) |
| `/api/v1/experience/search` | POST | Query past experience on-demand |
| `/api/v1/experience` | POST | Write a single experience entry |
| `/api/v1/experience/batch` | POST | Write multiple experience entries |

### Potential API Gap: Org GET by Slug

The current org endpoints need to be verified. If `GET /api/v1/orgs/<slug>` does not exist or does not return the personal statement, this is a targeted addition (not a new wave). Flag for Dante to verify during design.

---

## 11. Acceptance Criteria

### AC1: Identity Bootstrap

Given an agent definition file in the new format and valid credentials,
when the agent is dispatched via Claude Code,
then the agent calls the TeamForge API and loads its persona, responsibilities, relationships, and understanding from the database (not from markdown files).

### AC2: Team Context

Given a bootstrapped agent,
when the agent loads team context,
then it knows the full team roster (names, roles, slugs), active norms, and connected projects -- all from the API.

### AC3: Org Context

Given a bootstrapped agent,
when the agent loads org context,
then it has the sponsor's personal statement from the API.

### AC4: Bootstrap Confirmation

Given a successful bootstrap,
then the agent outputs a one-line confirmation including its name, role, team, and active project(s).

### AC5: Experience Query

Given a bootstrapped agent with a mid-session need for past context,
when the agent queries the experience search API with a natural language question,
then it receives semantically relevant results and incorporates them into its work.

### AC6: Experience Capture

Given a bootstrapped agent that has made observations during a session,
when the agent writes experience to the API (single or batch),
then the entries are stored with correct agent_id, team_id, observation_type, scope, and body, and are retrievable via future search queries.

### AC7: Credential Security

Given the agent definition files committed to git,
then no API key or secret appears in any committed file.
And the credential file at `~/.config/teamforge/credentials.json` is outside the repo.

### AC8: Fallback on API Failure

Given a dispatched agent when the TeamForge API is unreachable,
then the agent outputs a clear error message and does not proceed with no identity.
It does not silently fall back to markdown files.

### AC9: Fallback on Missing Credentials

Given a dispatched agent when the credential file does not exist,
then the agent outputs a clear error message explaining what is needed.

### AC10: Capstone Demo

Given the full system (API deployed, data seeded, credentials configured, agent files updated),
when the sponsor dispatches dante-tl and asks it to work on a project,
then Dante bootstraps from the API, dispatches a sub-agent, the sub-agent also bootstraps from the API, and both agents operate with their database-sourced identity.

---

## 12. Implementation Notes for Dante

These are observations and flags for the TL to consider during design. They are not requirements.

1. **Bash command safety.** The bootstrap involves `curl` and `cat` commands. Claude Code agents can run bash. But if the agent's `permissionMode` restricts bash, the bootstrap will fail. Verify that `permissionMode: default` allows unrestricted bash.

2. **JSON parsing.** The agent needs to parse JSON responses from curl. Claude Code agents can do this natively (they read the JSON output and extract fields). No `jq` dependency is required for the agent itself (only for the provisioning script).

3. **Agent UUID resolution.** The experience API requires `agent_id` as a UUID, not a slug. The agent gets its UUID from the `GET /api/v1/agents/<slug>` response (`id` field). It must store this for use in experience API calls.

4. **Team UUID resolution.** Similarly, the experience search API requires `team_id` as a UUID. The agent gets this from the `GET /api/v1/teams/<slug>` response.

5. **Context window budget.** A full agent identity (persona + responsibilities + relationships + understanding) could be 2,000-5,000 tokens. Team context (roster + norms + projects) adds another 500-1,000. Org context (personal statement) adds ~500. Total bootstrap: ~3,000-6,500 tokens. This is comparable to or less than the current 8-file markdown load. Experience is now on-demand, which is a net savings.

6. **Operating Model section.** The role-specific instructions at the bottom of each agent definition file (e.g., "There is no dedicated PO on this team") must be carried over from the current files. These are operational instructions that do not belong in the database -- they are about how this particular deployment of the agent works, not about the agent's identity. If Dante disagrees and thinks these belong in the database (perhaps as a team-level configuration), that is a design-level discussion.

7. **The `skills: openspec` line.** This is a Claude Code skill reference. It should be carried over if the agents need it. Dante to confirm.

---

## 13. Open Questions (For Design Phase)

| ID | Question | Owner |
|----|----------|-------|
| DQ1 | Does `GET /api/v1/orgs/<slug>` exist and return `personal_statement`? | Dante (verify API) |
| DQ2 | Should the Operating Model section move into the database as a team-level config, or stay in the agent definition file? | Dante (design decision) |
| DQ3 | Should the provisioning script be a Python script (more robust) or a bash script (simpler)? | Dante (design decision) |
| DQ4 | Should agents proactively query experience at bootstrap for high-priority items (e.g., "any critical process gaps from the last session"), or strictly on-demand? | Dante + Sponsor |
| DQ5 | Should the bootstrap confirmation include token count of loaded identity (for context window visibility)? | Dante (design decision) |

---

## Document Status

Complete. All blocking questions resolved. All API endpoints verified. Nautilus identity seeded and verified. Capstone demo operational.

Resolved during implementation:
- DQ1: GET /api/v1/orgs/<slug> exists and returns personal_statement. Confirmed.
- DQ2: Operating Model section stays in agent definition files, not in the database. Design decision.
- DQ3: Python script (provision_team.py) chosen. More robust than bash for JSON handling and template generation.
- DQ4: Strictly on-demand. No speculative queries at bootstrap. Strengthened query triggers added to CLAUDE.md template.
- DQ5: No token count in confirmation. Kept brief per the spec template.
