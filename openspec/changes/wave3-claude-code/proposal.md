# Proposal: Wave 3 -- Claude Code Integration

**Author:** Maya (RA)
**Date:** 2026-03-16
**Status:** Draft -- pending TL design review and sponsor approval
**Parent:** TeamForge Phase 1

---

## Problem Statement

Waves 1 and 2 built the backend: persistent identity (orgs, teams, agents) and persistent memory (experience capture, semantic search). But no agent actually uses them yet. Every agent on the Nautilus team still boots from markdown files on disk. Identity is read from `/ai_team/team/<agent>/persona.md`, `/ai_team/team/<agent>/responsibilities.md`, and so on. Experience is read from `/ai_team/experience/staging.md`. The database exists, the API is deployed and tested (54 integration tests, Green Cheese Test passing at 0.7038 similarity), but it has zero clients.

Wave 3 closes the gap. After this wave, when the sponsor types "spin up Nautilus on Project X" in VSCode, the agents load their identity from the TeamForge API, query experience from the API when they need it, and write observations back to the API at session close. The markdown files become a fallback, not the source of truth.

This is the sponsor's capstone demo: open VSCode, provision a team on a project, and have agents operate entirely from the database. No manual file editing. No copying markdown between repos.

---

## Scope

### In Scope

1. **Agent definition file rewrite** -- Replace the current markdown-file-reading agent definitions (`.claude/agents/*.md`) with API-bootstrapped definitions that instruct agents to call the TeamForge API on spin-up. The agent definition file becomes a thin launcher, not a container for identity content.

2. **Identity bootstrap flow** -- When an agent is dispatched, it calls `GET /api/v1/agents/<slug>` to retrieve its persona, responsibilities, relationships, understanding, and current scores. It also calls `GET /api/v1/teams/<slug>` for team context (roster, norms, active projects). This replaces reading 8+ markdown files.

3. **Experience retrieval integration** -- When an agent needs past context mid-session, it calls `POST /api/v1/experience/search` with a natural language query instead of reading markdown experience files. The agent definition instructs the agent on when and how to query experience.

4. **Experience capture integration** -- At session close (or mid-session when the agent has an observation worth recording), the agent calls `POST /api/v1/experience` or `POST /api/v1/experience/batch` to write observations back. This replaces appending to `staging.md`.

5. **Team provisioning flow** -- A mechanism for the sponsor (or TL) to say "spin up team X on project Y" and have the correct agent definition files generated or configured. This is the orchestration layer that connects the database to Claude Code's agent system.

6. **Credential management** -- How agents get the API key they need to authenticate. Must be secure, must not leak into conversation output, must work within Claude Code's constraints.

7. **Fallback behavior** -- What happens when the API is unreachable. Agents must not silently fail with no identity.

### Out of Scope

1. **New API endpoints** -- Wave 3 is a client-side integration. The API surface from Waves 1-2 is sufficient. If we discover a missing endpoint during design, it is a targeted addition, not a new wave.

2. **Management console** -- Wave 4.

3. **Performance evaluation workflow** -- Separate module, separate wave. Agents receive their `current_scores` as part of the identity bootstrap (already returned by the agent GET endpoint), but the review submission flow is not part of Wave 3.

4. **Norm management workflow** -- Separate module.

5. **Multi-repo agent definitions** -- Wave 3 targets the Crucible repo. Supporting arbitrary repos that can "import" TeamForge agents is a future concern.

6. **Automated experience migration** -- Moving existing markdown experience into the database. This was deferred from Wave 2. It can be a companion task but is not required for the integration to work -- the system starts with whatever experience is already in the database.

---

## Blocking Questions

### B1: How does Claude Code access environment variables or secrets?

**Context:** The agent needs an API key (`X-API-Key` header) to call the TeamForge API. Claude Code agents execute bash commands and can read files. The API key must be available to the agent without being hardcoded in the agent definition file (which is committed to git).

**Options:**
- (a) Agent reads the key from a `.env` file or environment variable at session start via a bash command.
- (b) The agent definition file references a path to a secrets file (e.g., `~/.config/teamforge/api_key`) that the agent reads.
- (c) The key is set as a Claude Code environment variable or project-level secret.

**My recommendation:** Option (a) -- the agent reads from an environment variable using a bash command (`echo $TEAMFORGE_API_KEY`). This is the simplest approach that keeps the key out of git. The agent definition file contains instructions to read the key, not the key itself. Flagging for Dante to confirm what Claude Code supports.

### B2: Should agent definition files be generated or hand-maintained?

**Context:** Today, each agent has a hand-written `.claude/agents/<name>.md` file. In the API-bootstrapped world, these files become thin launchers -- they all follow the same pattern (read credentials, call API, load identity). Should we:

- (a) **Generate them** from the database using a provisioning script (e.g., `python provision.py --team nautilus --project crucible`).
- (b) **Hand-maintain** a template that is parameterized (each file just has the agent slug and API URL, everything else is fetched at runtime).
- (c) **Single dispatcher** -- one agent definition file that accepts the agent name as a parameter.

**My recommendation:** Option (b) for Phase 1. Each agent gets a thin, nearly-identical `.md` file that differs only in the agent slug. This preserves Claude Code's native agent dispatch model (each agent is a named file). Generation (a) is a natural optimization for later, but hand-maintaining 8 small files is not burdensome. Option (c) changes the dispatch model and may not be compatible with how Claude Code discovers agents.

### B3: What is the sponsor's slug and team slug in the database?

**Context:** The bootstrap flow needs to know which org, team, and agent to query. The current data in the database needs to match what the agent definition files reference.

**Requirement:** Before Wave 3 can be tested, the Nautilus team's identity data must be seeded in the production database -- all agents, the team, and the org. This may already be partially done from Wave 1 testing, but it needs to be verified and complete.

### B4: What does "spin up Nautilus on Project X" actually mean mechanically?

**Context:** The sponsor's capstone demo is: type a command in VSCode, and the team loads. But Claude Code does not have a "spin up team" primitive. The sponsor interacts with Claude Code by dispatching individual agents or typing in the main chat.

**Options:**
- (a) **Manual dispatch** -- The sponsor says "use the dante-tl agent to start work on Project X." Dante bootstraps from the API and dispatches other agents as needed. "Spin up the team" means "dispatch the TL."
- (b) **Provisioning command** -- A bash script or Claude Code slash command that generates/updates agent definition files for a specific team-project combination, then the sponsor dispatches agents normally.
- (c) **Orchestrator agent** -- A special agent definition (e.g., `team-launcher.md`) whose sole job is to provision a team on a project and confirm readiness.

**My recommendation:** Option (a) for Phase 1, with (b) as a convenience layer. The TL is already the "always-warm hub" who dispatches other agents. The sponsor already interacts through the TL. Making "spin up" mean "dispatch the TL and tell it the project" is the simplest path that matches the existing operating model. A provisioning script (b) can handle the one-time setup of agent definition files per repo. Option (c) adds complexity without clear value in Phase 1.

---

## Non-Blocking Questions (Resolve During Design)

### NB1: Should the agent cache its identity for the session?

After the bootstrap API call, should the agent hold its identity in memory for the session, or re-fetch on every dispatch? Likely "cache for session" -- identity does not change mid-session. Dante's call.

### NB2: How verbose should the bootstrap output be?

When an agent bootstraps from the API, should it report what it loaded (for sponsor visibility), or load silently? The sponsor values transparency ("show your reasoning"), which suggests a brief confirmation: "Loaded identity from TeamForge API. Team: Nautilus. Project: Crucible. Roster: 8 agents."

### NB3: Should experience writes be automatic or explicit?

The agent definition can instruct agents to write experience at session close. But Claude Code sessions can end abruptly (user closes terminal). Should the agent write experience proactively throughout the session, or batch at the end? This was resolved as "any time, configurable" in Wave 2 (B1). The integration spec needs to define the default behavior.

---

## Spec Breakdown

### Spec 1: agent-bootstrap (BLOCKING -- write this first)

The core integration spec. Covers:
- Agent definition file structure (the new thin-launcher format)
- Bootstrap flow (API calls on agent dispatch)
- Identity loading (what data the agent receives and how it uses it)
- Experience retrieval integration (how and when agents query experience)
- Experience capture integration (how and when agents write experience)
- Team provisioning flow (how agent definition files get created for a team)
- Credential management (how the API key reaches the agent)
- Fallback behavior (what happens when the API is down)
- The sponsor's capstone demo flow end-to-end

This single spec covers the entire Wave 3 scope. The integration is conceptually one feature with several facets, not several independent features. Splitting it would create artificial boundaries.

### Companion Task: nautilus-seed-verification (NON-BLOCKING)

Verify that the Nautilus team's identity data is complete and correct in the production database. All 8 agents, the team entity, the org entity, and at least one project reference. This is a prerequisite for testing but not a spec -- it is a data verification task.

---

## Dependencies

| Dependency | Status | Impact |
|-----------|--------|--------|
| Wave 1 CRUD API deployed | DONE | Agent, team, org endpoints available |
| Wave 2 experience API deployed | DONE | Experience write and search endpoints available |
| Green Cheese Test passing | DONE (0.7038) | Semantic search is functional |
| Nautilus identity data seeded in DB | NEEDS VERIFICATION | Cannot test bootstrap without data |
| Claude Code agent definition format stable | ASSUMED | If Anthropic changes the format, definitions need updating |

---

## Risks

### R1: Claude Code agent context window consumption

The current markdown-based system loads 8+ files into the context window. The API-based system loads the same information via API responses. If the API returns the full persona, responsibilities, relationships, and understanding as text, the context window consumption is similar. The difference is that experience is loaded on-demand (smaller initial footprint) rather than all-at-once.

**Mitigation:** Measure the token count of a full bootstrap API response. If it exceeds what the markdown files consume, consider a "lean bootstrap" endpoint that returns a summary. Flag for Dante.

### R2: API latency at bootstrap

Every agent dispatch now includes 2-3 API calls (read credential, fetch agent identity, fetch team context). If the API is slow (cold start on Cloud Run), the agent spin-up time increases noticeably.

**Mitigation:** Cloud Run minimum instances = 1 (already configured in Wave 1). Monitor cold start frequency. If needed, add a health check ping before dispatch.

### R3: Credential exposure

The API key is a secret. If the agent reads it via a bash command, the key appears in the conversation output (Claude Code shows bash command results). The sponsor would see it, which is acceptable (it is their key), but it should not be logged or shared.

**Mitigation:** The agent reads the key silently and does not echo it in conversation. The agent definition instructs: "Do not display the API key in your output."

### R4: Markdown-to-API parity

The markdown identity files contain nuance that may not have been captured when the data was seeded into the database. If Dante's relationships.md contains 30 lines of carefully written relationship dynamics, but the database `relationships` field contains a truncated version, the agent's behavior will degrade.

**Mitigation:** The nautilus-seed-verification task must compare markdown source files against database content for completeness. This is a data quality task, not a code task.

### R5: Agent definition file maintenance burden

With 8 agents, maintaining 8 nearly-identical agent definition files is manageable. But if the team grows or multiple teams are provisioned, this becomes tedious. Generation (B2 option a) becomes necessary.

**Mitigation:** Keep Phase 1 manual. Add generation as a Wave 3.5 optimization if the pain is real.

---

## Success Criteria

1. An agent dispatched via Claude Code loads its identity entirely from the TeamForge API -- no markdown file reads for persona, responsibilities, relationships, or understanding.
2. The agent knows its team context (roster, active projects, norms) from the API.
3. The agent queries experience via the semantic search API when it needs past context, instead of reading markdown files.
4. The agent writes experience observations back to the API during or at the end of a session.
5. The sponsor can dispatch the TL agent, specify a project, and have the TL bootstrap the full team from the database.
6. The API key is not hardcoded in any file committed to git.
7. If the API is unreachable, the agent reports the problem clearly rather than proceeding with no identity.
8. **Capstone demo:** The sponsor opens VSCode, dispatches Dante on a project, Dante loads from the API, dispatches a sub-agent, the sub-agent also loads from the API, and both agents reference their database-sourced identity correctly.

---

## Document Status

Draft. Blocking questions B1-B4 need resolution (B1 and B2 are TL decisions, B3 is a verification task, B4 is a sponsor/TL decision). Non-blocking questions NB1-NB3 can be resolved during design.

Pending:
- TL design review
- Sponsor approval of scope and capstone demo definition
- Resolution of blocking questions
