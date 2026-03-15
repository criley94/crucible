# TeamForge — Project Specification

**Status:** Starting point for implementation planning
**Audience:** Platform engineering team (Claude Code)
**Note to team:** This document describes the vision and key architectural decisions for TeamForge. It is not a final implementation spec. The owner will work directly with the team to finalize implementation details, service choices, file structure, and phasing. Treat this as the north star — bring your questions, alternatives, and recommendations to those sessions.

---

## What This Is

TeamForge is a persistent, evolving multi-agent team system built on GCP. It allows the owner to spin up named, role-defined agent teams that start "green" (no shared history) and grow into high-performing units over time through accumulated experience — both individually and as a team.

The key insight driving this system: **it's not just individual agents that learn, it's the team dynamic itself.** How agents communicate with each other, challenge each other, divide work, and build rapport are all things that should persist, evolve, and be available on the next project.

Primary use cases are software development and content creation workflows.

---

## Core Concepts

### The SOUL

Every agent has a SOUL — a persistent identity definition that includes:

- A name
- A personality and communication style
- A defined role and area of expertise
- How they typically engage with other specific team members
- Their growth history (what they've learned, how they've changed)

The SOUL is not static. It starts from a template at team creation and evolves over time as the agent works on projects and the audit process runs. A SOUL at project 10 should read differently than a SOUL at project 1.

### The Team

A team is a named collection of 4–6 agents with defined roles, assembled from a bootstrap process. Teams have:

- A **tech lead agent** who knows the full team composition, the rules of engagement, and how to orchestrate the team toward a goal
- **Individual member agents**, each with their own SOUL and role
- A **shared team memory** that captures dynamics, patterns, and lessons that belong to the team as a whole rather than any individual

Teams can be reused across projects. The owner chooses at project start whether to create a new team or load an existing one.

### The Bootstrap

Every session begins by reading a bootstrap file. The bootstrap:

- Identifies whether this is a new team or an existing one
- If new: defines team composition, roles, and initial SOUL templates
- If existing: loads the tech lead's current state, which then retrieves and instantiates each team member with their current SOUL and the current shared team memory
- Hands off to the tech lead to brief the team and begin work

### The Audit Agent

At the end of every project, a dedicated audit agent sweeps all stored interaction data and extracts two categories of lessons:

- **Agent-specific lessons:** growth, role insights, communication preferences, things an individual agent has learned about themselves or their work
- **Team-level lessons:** patterns in how the team worked together, friction points that got resolved, communication shortcuts that emerged, trust that developed between specific agents

The audit agent writes these back to the appropriate memory stores so they are available on the next bootstrap.

---

## Target Architecture

### Platform

- **GCP** — all infrastructure lives here, on the owner's existing Cloud VM
- **Vertex AI Agent Builder** — the core platform for agent definition, deployment, and orchestration
- **Agent Development Kit (ADK)** — Python framework for building agents, defining SOULs via system prompts, and wiring team interactions
- **Vertex AI Agent Engine** — managed runtime for deploying and scaling agents in production
- **Vertex AI Memory Bank** — persistent long-term memory store; backs both individual SOUL evolution and shared team memory
- **Agent Engine Sessions** — short-term memory within a single project session
- **Agent2Agent (A2A) protocol** — communication between agents within a team

### Memory Architecture

Two distinct memory scopes must be maintained:

**Individual memory (per agent, per team)**
Scoped to `agent_id + team_id`. Stores SOUL evolution: growth notes, role lessons, communication preferences, and how this agent relates to each other specific team member. The audit agent writes here. The bootstrap reads here to reconstitute each agent's current state.

**Shared team memory (per team)**
Scoped to `team_id`. Stores team-level dynamics: patterns of collaboration, trust that has developed between specific agents, communication shortcuts, lessons from how the team handled past challenges together. The audit agent writes here. The tech lead reads here during bootstrap to inform how it briefs and orchestrates the team.

### Agent Identity

Each agent is defined in ADK as an `LlmAgent` with:

- A unique `name` (their actual name, not a role label)
- A `description` (used by the tech lead for routing decisions)
- An `instruction` (their system prompt — this is their SOUL, injected dynamically from memory at session start using ADK's `{state_key}` templating)

The SOUL in the instruction field should include: name, personality, communication style, role expertise, current growth state, and known relationships with other team members by name.

### Bootstrap Flow

```
User initiates session
  → Bootstrap file read
  → New team OR existing team?
      → New: create team record, instantiate agents from SOUL templates
      → Existing: load team_id, retrieve all agent SOULs + shared team memory from Memory Bank
  → Tech lead instantiated with full team context
  → Tech lead briefs team members (each instantiated with their current SOUL)
  → Team ready for project work
```

### Audit Flow

```
Project concludes
  → Audit agent triggered
  → Sweep: all session events, agent interactions, tool outputs
  → Extract: agent-specific lessons → write to individual memory per agent
  → Extract: team-level lessons → write to shared team memory
  → Memory revisions created (Memory Bank maintains history)
  → Session closed
```

---

## What "Green to High-Performing" Means

This is the core value proposition of TeamForge. It should be treated as a first-class design requirement, not a side effect.

On project 1, a new team has no shared history. The tech lead knows the rules and roles. The agents have their initial SOULs. They are capable but generic. They don't know each other yet.

By project 5–10, the team should demonstrably behave differently:

- Agents should reference past shared experiences in how they frame contributions
- The tech lead should route work differently based on learned team strengths
- Communication between specific agents should reflect built rapport or known friction
- The audit agent's outputs should show compounding richness over time

The system should be designed so this evolution is observable and inspectable — not just happening invisibly. The owner wants to be able to read a team's shared memory and see the arc of how they've grown.

---

## The Future State (Not in Scope Now)

The owner has a longer-term vision that should be kept in mind during architecture decisions, even though it is not part of this build:

A persistent "right hand" agent — likely built on a maturing version of OpenClaw or equivalent — will eventually sit above the team layer. This agent will know the owner's preferences, goals, and working style deeply, and will be capable of directing TeamForge teams on the owner's behalf without requiring the owner to be present for every session.

**Implication for this build:** Do not design TeamForge as a closed system. The bootstrap and orchestration layer should be designed to accept direction from an external orchestrator in the future, not just from a human user. The tech lead agent's input interface should be abstracted enough that "human types a goal" and "orchestrator agent passes a goal" are equivalent.

---

## What the Team Should Bring Back

This document is a starting point. Before implementation begins, the platform team should review it and return with:

- Recommended file and repo structure for the project
- Proposed phasing (what gets built first, what comes later)
- Any GCP service alternatives or additions worth considering
- Questions about any ambiguity in the spec
- A proposed schema for SOUL storage in Memory Bank (what fields, what format)
- Recommendations on how to make team evolution observable/inspectable by the owner

The owner will review these with the team and finalize before implementation work begins.

---

## Constraints and Principles

- **GCP-native first.** Prefer managed GCP services over self-hosted solutions wherever reasonable.
- **SOULs are sacred.** Agent identity and memory should never be silently reset. Any destructive operation on a SOUL or team memory requires explicit intent.
- **The audit agent is non-negotiable.** The loop only works if lessons are captured. Audit must be treated as a required step, not optional cleanup.
- **Human stays in the loop now.** The current build has the owner directing the tech lead directly. Do not add autonomous scheduling or self-triggering behavior in this phase.
- **Design for the future orchestrator.** See future state note above.
- **Claude models preferred.** The system runs on Claude Code / Claude models via Vertex AI Model Garden. Gemini is available as a fallback or for specific tasks if justified.
