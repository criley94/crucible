## Context

Today, attaching a team to a project requires manually creating `.claude/agents/*.md` files and a `CLAUDE.md`. This was done by hand for crucible and green-cheese-test. The sponsor wants: open a new folder, run one thing, talk to the TL.

The existing patterns to build on:
- Agent definition files use YAML frontmatter + markdown body (see `.claude/agents/dante-tl.md`)
- CLAUDE.md contains the TL bootstrap instructions and is auto-loaded by Claude Code
- Credentials live at `~/.config/teamforge/credentials.json`
- The API roster endpoint returns all agents with their roles, slugs, and descriptions

## Goals / Non-Goals

**Goals:**
- One-command team provisioning on any project
- TL auto-detected from roster (no hardcoded names)
- Generated files follow the exact patterns already working in crucible
- Seed agent is team-agnostic -- works for any team in the org
- Foundation for future GUI-based provisioning

**Non-Goals:**
- Building the management console GUI (Wave 4, Lena designs)
- Multi-org support (one org per credentials file for now)
- Modifying the TeamForge API
- Handling team changes after provisioning (re-run the seed to update)

## Decisions

### AD1: Seed Agent as Claude Code Agent Definition
The seed file is a standard `.md` agent definition file with YAML frontmatter. It lives at `~/.config/teamforge/seed.md`. Invoked via `claude --agent ~/.config/teamforge/seed.md`.

Alternative: A Python CLI script. Rejected -- the sponsor wants to interact with an agent, not run a script. The agent can ask questions, confirm choices, and report what it did.

### AD2: TL Auto-Detection
The seed agent queries `GET /api/v1/teams/{slug}`, iterates the roster, and finds the agent with `role: "Tech Lead"`. That agent's slug becomes the CLAUDE.md bootstrap target.

Alternative: Hardcode TL slug per team in credentials. Rejected -- the roster already has this data.

### AD3: Team Selection
If the credentials file has a `team_slug`, use it automatically. If there are multiple teams in the org and no default, the seed agent asks the user which team to provision.

To discover available teams, the seed agent queries: `GET /api/v1/orgs/{slug}` -- though this doesn't return a team list directly. For now, rely on `team_slug` in credentials. Multi-team selection is a management console concern.

### AD4: Generated File Templates
The seed agent generates files using inline templates that match the existing patterns:
- **CLAUDE.md**: TL identity preamble + bootstrap steps + experience protocol + operating model. Parameterized by TL slug, team slug, org slug.
- **.claude/agents/{slug}.md**: YAML frontmatter (name, description, model, permissionMode) + bootstrap body. Parameterized by agent slug, name, role, description.
- **.claude/settings.local.json**: Pre-approved tool permissions for the project directories.

Templates are embedded in the seed agent file itself -- no external dependencies.

### AD5: Idempotency
If `.claude/agents/` already has files or `CLAUDE.md` already exists, the seed agent warns and asks whether to overwrite. This prevents accidental destruction of customized files.

### AD6: Install Script
A simple bash script (`scripts/install_seed.sh`) that:
1. Copies `seed.md` to `~/.config/teamforge/seed.md`
2. Checks that `~/.config/teamforge/credentials.json` exists
3. Checks that `gcloud` is available
4. Prints usage instructions

### AD7: Operating Model Section in CLAUDE.md
The operating model section is team-specific. For Nautilus, it includes the No-PO amendment. Rather than trying to generalize operating models across all teams, the seed agent includes a generic operating model and the TL's persona (loaded from the API) governs the specifics.

## Risks / Trade-offs

- **Seed file size**: Embedding templates in the seed agent file makes it long (~200 lines). Acceptable -- it's a one-time provisioning agent, not a daily-use file.
- **Template drift**: If the bootstrap protocol changes, the seed file's templates need updating. Mitigated by keeping the seed in the crucible repo and re-running install.
- **No team list API**: Currently no endpoint to list all teams in an org. The seed relies on `team_slug` in credentials. This is fine for now -- multi-team discovery is a management console feature.
- **Claude Code `--agent` path support**: Using a full path (`~/.config/teamforge/seed.md`) as the agent argument. This works in current Claude Code versions.
