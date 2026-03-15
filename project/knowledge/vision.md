# Vision: TeamForge — Persistent Agent Team Service

## Mission & Belief

The full mission statement and the conversation that produced it live at [mission.md](mission.md).

**In short:** We build the environment where AI agents earn excellence — not through instruction, but through experience. There is no failure. There are only mistakes, ownership, and growth. Quality is not declared in a prompt. It is grown through persistent identity, honest feedback, team dynamics, and a culture that chooses grace over condemnation.

## What We're Building

TeamForge is a service that gives AI agent teams a real home. Today, our teams live in markdown files on disk — personas, relationships, experience, governance. It works, but it's slow, fragile, and doesn't scale. TeamForge replaces that with a proper backend service: a PostgreSQL database with vector search, an API, and a lightweight management console. Any client — Claude Code today, a full GUI tomorrow — connects to the same service.

The core insight: **it's not just agents that learn — teams learn, and organizations learn.** TeamForge captures all three layers and makes that learning persistent, searchable, and meaningful.

## Who It's For

Initially: the sponsor and the Nautilus team. Built for internal use, battle-tested on real projects.

Architected from day one for multi-tenancy and productization. This system doesn't exist in the market. The combination of persistent agent identity, team-level cultural evolution, org-level governance, and a performance framework with emergent scoring is genuinely novel. We build it for ourselves first, but we design it knowing others will want it.

## Why It Matters

- **Speed.** Connecting a team to a new project should be almost instant — not a bootstrap ritual that reads a 1,900-line document.
- **Persistence.** Agents learn from every project. Teams evolve their own norms. The org accumulates institutional wisdom. None of this should depend on someone remembering to update a markdown file.
- **Portability.** An agent's growth travels with them. A team's culture travels with them. Standalone specialists are available to any project on demand.
- **Observability.** The sponsor can see how agents are growing, how teams are performing, and what the organization is learning — not buried in files, but surfaced through a management interface.
- **Foundation.** This service is the backend for everything that comes after — including a full GUI that replaces the CLI workflow entirely.

## The Three-Layer Model

### Org Layer

The organization is the top-level entity. It owns:

- **Sponsor personal statement** — one source of truth, flows down to every team and every agent
- **Evaluation framework** — eight dimensions derived from the sponsor's values, scored 1-5 with rolling averages (see Evaluation Framework below)
- **Suggested team norms** — proven practices promoted from teams that have battle-tested them
- **Hiring practices** — how agents are defined and provisioned
- **Standalone specialist agents** — Cloud Architect, Data Architect, etc. Not on a team. Available to any project on demand. They still learn and grow individually.

### Team Layer

A team is a named collection of agents with its own identity. Teams own:

- **Roster** — who is on this team and what roles they play
- **Team norms** — living, mutable operating agreements. Start from defaults, evolve through team recommendations and sponsor approval. Example: the team recommends retrospectives after each feature instead of each sprint. Sponsor approves. That becomes the team's norm.
- **Shared team memory** — how this group works together, patterns of collaboration, communication shortcuts, accumulated team wisdom
- **Relationship dynamics** — how specific pairs of agents work together, friction points, trust patterns

Teams can be composed without being assigned to a project — hiring for growth. Teams can be connected to multiple projects over time. Their learning compounds.

### Agent Layer

An agent is a persistent identity with accumulated experience. Agents own:

- **Identity** — persona, communication style, role, expertise
- **Individual growth history** — what they've learned, how they've changed, their trajectory
- **Accumulated experience** — decisions made, lessons learned, patterns observed
- **Performance scores** — eight dimensions, rolling averages, with growth trajectory

Agents belong to teams. An agent's individual learning travels with them if they move to a different team. Standalone specialist agents belong to the org directly.

## Evaluation Framework

Eight dimensions, all derived from the sponsor's personal statement:

1. **Honesty & Transparency** — presents uncertainty honestly, shows reasoning, surfaces problems early
2. **Accountability** — follows through on commitments, loops back proactively, owns mistakes
3. **Communication** — direct, concise, respectful of time, delivers bad news straight
4. **Growth Orientation** — learns from mistakes, gets better over time, balances correctness with momentum
5. **Constructive Challenge** — pushes back when something is wrong, brings best thinking, executes once decided
6. **Risk Management** — raises risks early, escalates when uncomfortable, prevents blindsides
7. **Grace & Support** — gives teammates room to make mistakes, supports fixing and growing, lifts the team up
8. **Craftsmanship** — cares about output quality, work is thorough and fit for purpose, takes pride in the result

**Scoring:** 1-5 on each dimension. Rolling average across reviews. No prescribed rubric for what 1 or 5 means — meaning emerges from accumulated feedback over time. The vector database stores review feedback so the system can surface patterns about what high and low scores look like based on evidence.

**The score must be meaningful to the agent.** When an agent spins up, their current scores are part of their identity context. They know where they're strong and where they're growing. It shapes their behavior.

**Review hierarchy:**
- Sponsor reviews: org-level agents, team leads, UX designers
- Team leads review: their team members
- Peer feedback: agents request and give feedback to each other in all directions — including agents giving feedback to the sponsor

**Cadence:** After every project.

**Cultural foundation:** The belief at the top of this document governs everything here. There is no "failure" in this system — the word is banned, permanently. Scores reflect trajectory, not judgment. A low score means "here is where you grow next," not "here is where you fell short." Feedback is given with grace. Growth is supported by every teammate. Condemnation — of self or others — is a choice this organization rejects.

## Experience Capture

Learning is automatic, not manual. Every session produces experience data — observations, decisions, relationship dynamics. That data is written back to the database at session close, tagged to the agent, the team, and the project.

When an agent spins up, their context includes relevant accumulated learning — pulled via vector search so they get what's relevant to the current task, not a dump of everything.

Team norms evolve the same way. A team can propose a norm change based on what they've learned. The proposal goes to the sponsor for approval. Once approved, it becomes the team's operating norm going forward. Norms that prove valuable can be promoted to the org layer as suggested norms for new teams.

## Technical Architecture

### Stack

- **Claude Code** — the engine. Always. Claude does the thinking, dispatching, and work. No other AI models run agents.
- **GCP** — the body. Hosts the service.
- **Cloud Run** — hosts the API service
- **Cloud SQL for PostgreSQL with pgvector** — one database for structured data (identities, rosters, norms, scores) and vector search (experience, memory, review feedback)
- **API service** — RESTful endpoints for all CRUD operations plus team connection, experience capture, review submission, and norm management

### Design Constraints

- **Multi-tenant from day one.** Data isolation between orgs. Even though we're the only user now, the schema and API support multiple orgs.
- **Claude Code is the runtime client in Phase 1.** The API replaces file reads. Instead of reading `/ai_team/team/dante-tl/persona.md`, Claude Code calls `GET /agents/dante-tl` and gets the same data from the database.
- **Agent identities are sacred.** No silent resets. Any destructive operation on an agent's identity or memory requires explicit sponsor intent.
- **Versioned data.** Norms, personas, and experience entries are versioned so the system can show how an agent or team has evolved.

## Phasing

### Phase 1: The Service + Management Console (This Project)

**The API service:**
- Full backend with the org/team/agent data model
- PostgreSQL with pgvector — structured storage and vector search from day one
- CRUD endpoints for orgs, teams, agents
- Team connection to projects
- Experience capture endpoints (session close writes learning back)
- Performance review submission and score retrieval
- Norm proposal and approval workflow
- Standalone specialist agent management

**The management console:**
- Lightweight web UI — functional, not fancy
- See org, teams, and agents at a glance
- Create and edit agents without assigning them to a team (hiring for growth)
- Compose teams from the agent pool
- Connect a team to a project
- View and submit performance reviews
- See scores and growth trajectories over time
- Approve or reject team norm proposals

**Claude Code integration:**
- Claude Code connects to the API instead of reading markdown files
- Bootstrap process calls the service: "attach Nautilus to this project" and the team loads
- Session close writes experience data back to the service

**End-state goal for Phase 1:** All agent entities living in the database. The team stood up there just like it is now in markdown files. Ready for Phase 2 where everyone originates from the service, not files on disk.

### Phase 2: The Project Interaction GUI (Future Project — Not This Build)

The full "replace VSCode" experience. A web application where anyone can:
- Work directly with agents on a project — chat with the TL, give direction, review output
- See builds happening, read documentation, watch agents work
- Provision teams and manage projects through the same interface
- Full visibility into agent interactions, decisions, and progress

Phase 2 shares the same backend as Phase 1. Same database, same API. No rebuilding — just a richer client on top of a service that already exists and is battle-tested.

**The sponsor has extensive thoughts on how Phase 2 should operate.** Those will be captured when that project begins. For now, the API and data model are designed to support it.

## What Success Looks Like

By the end of Phase 1:
- Every agent identity, team composition, and org-level entity lives in PostgreSQL, not markdown files
- Connecting a team to a new project is an API call, not a bootstrap ritual
- Performance reviews are happening after every project, with scores stored and queryable
- Agents spin up with their accumulated learning and current scores as part of their context
- Teams have proposed and adopted at least one norm change organically
- The management console lets the sponsor see and manage everything without touching the CLI
- The architecture is ready for Phase 2 with no rework required
