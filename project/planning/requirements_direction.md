# Requirements Direction: TeamForge Phase 1

**Author:** Maya (Requirements Architect)
**Date:** 2026-03-15
**Status:** Discovery -- Wave 1 blocking questions resolved, spec work beginning
**Project:** TeamForge (Crucible)

---

## 1. Purpose

This document maps the requirement landscape for Phase 1 of TeamForge. It identifies the major feature domains, calls out ambiguities that need sponsor clarification before specs can be written, proposes a sequencing for spec work, and flags risks of over-scope or contradiction.

This is not a spec. It is the document that tells us what specs to write, in what order, and what questions to answer first.

---

## 2. Major Requirement Domains

I have identified nine feature domains for Phase 1. Each will need at least one spec (some will need several).

### Domain 1: Data Model and Schema

The foundational three-layer model: Org, Team, Agent. This drives everything else.

**What it covers:**
- Org entity (sponsor personal statement, evaluation framework definition, suggested norms, hiring practices)
- Team entity (roster, team norms, shared memory, relationship dynamics)
- Agent entity (identity/persona, growth history, accumulated experience, performance scores)
- Standalone specialist agents (org-level, not team-bound)
- Project as a reference entity (identifier + basic metadata, not lifecycle-managed)
- Multi-tenant isolation between orgs
- Current-state storage with last-updated timestamps (no version history, no rollback)
- pgvector column design for experience/memory/review feedback

### Domain 2: Core CRUD API -- Orgs, Teams, Agents

The basic create/read/update/delete surface for all three layers.

**What it covers:**
- Org management (create, read, update)
- Team management (create, read, update, list)
- Agent management (create, read, update, list)
- Standalone specialist agent management (create, read, update, assign to org)
- Agent identity protection (destructive operation safeguards)

### Domain 3: Team Composition and Project Connection

Assembling teams from the agent pool and connecting them to projects.

**What it covers:**
- Add/remove agents from a team roster
- Create agents without assigning to a team (hiring for growth)
- Connect a team to a project (project as reference entity)
- Disconnect a team from a project
- Multiple projects per team over time (historical connection tracking)

### Domain 4: Experience Capture

On-demand experience storage and retrieval.

**What it covers:**
- Session close writes observations, decisions, relationship dynamics back to the database
- Experience is hybrid: structured metadata (agent_id, team_id, project_ref, timestamp, observation_type) + free-text body
- Free-text body gets vector-embedded for later retrieval
- Experience retrieved on-demand via API query (NOT front-loaded at spin-up)
- Retrieval uses vector similarity ranked by relevance, scoped by structured filters
- Agent spins up lean; queries experience when hitting a specific problem

### Domain 5: Performance Evaluation

The eight-dimension review system.

**What it covers:**
- Review submission (sponsor reviews, TL reviews, peer feedback)
- Score storage (1-5 per dimension, rolling averages)
- Review hierarchy enforcement (who can review whom)
- Score retrieval and growth trajectory queries
- Review feedback stored as vectors for pattern surfacing
- Agent context includes current scores at spin-up

### Domain 6: Norm Management

The team-level governance workflow.

**What it covers:**
- Team proposes a norm change
- Sponsor approves or rejects
- Approved norms become the team's operating norms
- Org-level suggested norms (promoted from proven team norms)
- Default norms for new teams

### Domain 7: Claude Code Integration

The client integration that replaces markdown file reads.

**What it covers:**
- API calls replace file reads for agent identity, team composition, org context
- Bootstrap flow: "attach team X to project Y" loads agent identity + scores + team context (lean)
- Experience is NOT loaded at bootstrap -- agents query on-demand when they need it
- Session close writes experience back

### Domain 8: Management Console

Lightweight web UI. Comes last. Thin client consuming the API.

**What it covers:**
- Org/team/agent dashboard views
- Agent creation and editing (without team assignment)
- Team composition management
- Project connection management
- Performance review submission and score viewing
- Growth trajectory visualization
- Norm proposal approval/rejection interface

### Domain 9: Infrastructure and Deployment

GCP deployment and operational concerns.

**What it covers:**
- Cloud Run service configuration
- Cloud SQL for PostgreSQL with pgvector provisioning
- Multi-tenant data isolation at the infrastructure level
- Authentication: API key per org, header-based, org-scoped data (Phase 1)
- Schema and API designed for multi-user and RBAC (future, not built now)
- CI/CD pipeline

---

## 3. Ambiguities and Gaps

### Resolved (2026-03-15)

**A1. What is a "project" in this system?**
RESOLVED: A project is a reference entity, not a managed lifecycle entity. It has an identifier and basic metadata (name, description). TeamForge does not manage the project's lifecycle. Key mental model: "Agents are ON projects. They don't live INSIDE of projects." Agent identity, experience, and growth live in TeamForge regardless of which project they are on.

**A2. What does "versioned data" mean, specifically?**
RESOLVED: Versioning is dropped as a requirement. The sponsor explicitly rejected rollback mechanics: "That's not real world thinking, and I don't want to bring that to agents either." Store current state with last-updated timestamps. Forward evolution only. No audit trail beyond what git provides.

**A4. Shared team memory vs. agent accumulated experience -- what is the boundary?**
RESOLVED: The system stores all experience. Retrieval surfaces what is relevant. What an agent does with the experience -- whether they absorb it, act on it, or disregard it -- is the agent's judgment, shaped by their scores and identity. The system does not curate or filter for growth areas. It surfaces. Agents decide.

**A9. What is the shape of experience data?**
RESOLVED: Hybrid structure. Structured metadata (agent_id, team_id, project_ref, timestamp, observation_type) + free-text body that gets vector-embedded. CRITICAL: Experience is NOT front-loaded at spin-up. It is retrieved on-demand. Agent spins up lean (identity, scores, team context). When the agent needs experience, it queries the API with a specific question. System returns results ranked by vector similarity, scoped by structured filters. The sponsor compared this to "start high level and dig down."

**A16. What is the authentication and authorization model for the API itself?**
RESOLVED: Phase 1 uses API key per org, header-based auth, org-scoped data. No RBAC yet. BUT the schema and API must support multi-tenant and multi-user from day one. The sponsor may offer this as SaaS and may give other human org members access. We do not build the full auth system now, but we do not make any decisions that close the door on it.

### Open -- Blocking for Wave 2+ Specs

**A3. What are "hiring practices" at the org level?**
The vision lists "hiring practices" as something the org owns. Not elaborated. Is this templates for creating new agents? A policy document? A workflow? Needs sponsor definition or explicit deferral.

**A5. Relationship dynamics -- what is the data model?**
Teams own "relationship dynamics -- how specific pairs of agents work together." Is this agent-authored prose stored as vectors? Structured pair ratings? Both? Needed for experience capture spec.

**A6. "No prescribed rubric" -- how does the system bootstrap?**
At the start there is no accumulated feedback. Do agents start with no scores? A default middle score? Sponsor calibration reviews? Needed for performance evaluation spec.

**A7. Peer feedback mechanics -- scored or unscored?**
Are peer feedback submissions scored on the same eight dimensions and factored into rolling averages? Or is peer feedback qualitative only? Needed for performance evaluation spec.

**A8. "After every project" -- what triggers a review cycle?**
Manual? Automatic on team disconnection? On-demand? Needed for performance evaluation spec.

**A10. What does "relevant" mean in vector retrieval?**
Relevant to the current project? Current task? Agent's role? Retrieval strategy needed. Partially technical (Dante), partially requirements (intent). Needed for experience capture spec.

**A11. Who can propose a norm?**
Any agent? Only the TL? Team consensus? Needed for norm management spec.

**A12. What are "default norms for new teams"?**
Source of defaults? Hardcoded? Org-level suggested norms? Sponsor-defined? Needed for norm management spec.

### Open -- Non-Blocking for Wave 1

**A13. What is the authentication model for Claude Code calling the API?**
Folded into A16 resolution: API key per org, header-based. Claude Code uses the org API key. Specific integration mechanics are a Wave 3 concern.

**A14. What happens when the API is unavailable?**
Fallback strategy for Claude Code. Wave 3 concern.

**A15. Who uses the management console?**
Single-user? Multi-user? Role-based access? Wave 4 concern.

**A17. "Agent identities are sacred" -- what counts as a destructive operation?**
Needs definition for API safeguard design. Can be resolved during Wave 1 spec review.

---

## 4. Spec Sequencing

### Wave 1: Foundation (IN PROGRESS)

1. **Data Model and Schema** -- everything else depends on this.
2. **Core CRUD API (Orgs, Teams, Agents)** -- the basic surface area. Tightly coupled with schema.
3. **Infrastructure and Deployment** -- Cloud Run, Cloud SQL, auth model.

### Wave 2: Core Workflows

4. **Team Composition and Project Connection**
5. **Experience Capture**
6. **Performance Evaluation**

### Wave 3: Governance and Integration

7. **Norm Management**
8. **Claude Code Integration**

### Wave 4: Console

9. **Management Console**

---

## 5. Flags: Unclear, Contradictory, or Potentially Over-Scoped

### Potential Over-Scope for Phase 1

**F1. Vector search sophistication.**
PARTIALLY RESOLVED by A9: on-demand retrieval simplifies the spin-up path. But the retrieval quality question remains. For Phase 1, recommend a simple similarity search with structured filters and iterate. Flag for Dante to scope during design.

**F2. Growth trajectory visualization.**
Wave 4 concern. Deferred.

**F3. "The architecture is ready for Phase 2 with no rework required."**
Recommend reframing as: "The data model and API are designed with Phase 2 in mind, and no known Phase 2 requirement forces a breaking schema change." Testable. "No rework required" is not.

### Unclear Requirements

**F4. Review cadence vs. project boundaries.**
Open. Wave 2 concern.

**F5. Standalone specialist agents.**
Open. Lifecycle questions remain. Wave 1 schema must account for them (org-level agents without team membership), but the full lifecycle is Wave 2+.

**F6. "Agents giving feedback to the sponsor."**
Open. Culturally important. Wave 2 concern.

### Tensions

**F7. "Multi-tenant from day one" vs. "initially the sponsor and the Nautilus team."**
RESOLVED by A16: Schema and API support multi-tenant. Auth is simple (API key per org). Full RBAC deferred. Door stays open for SaaS and multi-user.

---

## 6. Additional Sponsor Direction (2026-03-15)

- Lena is not needed until Wave 4 (console). Do not involve her in DB/API work.
- Frank writes and executes UAT on every feature. UAT test cases must be confirmed by the sponsor before execution.
- The management console is a thin client. API-first. Console does not drive API design.
- Phase 1 is almost exclusively DB and API layer.

---

## 7. Document Status

Updated 2026-03-15 with sponsor resolutions for A1, A2, A4, A9, A16 and additional sponsor direction. Wave 1 spec work beginning. Remaining open questions are non-blocking for Wave 1.
