## Why

New projects require manual setup of agent definition files before a team can work on them. The sponsor's workflow should be: open a new project folder, invoke one command, and be talking to the team lead. Today that requires copying files and editing slugs by hand. This change creates an automated provisioning flow so any team can be attached to any project with a single invocation.

This also sets the foundation for the long-term management console UI, where Lena will design a GUI for team provisioning. The same API calls and file generation logic will power both the seed agent (now) and the GUI (later).

## What Changes

- A global **seed agent file** is installed at `~/.config/teamforge/seed.md` -- a Claude Code agent definition that bootstraps from the TeamForge API
- The seed agent reads credentials, asks which team to provision (or auto-selects if only one), and calls the API to get the roster
- It generates all project files: `CLAUDE.md` (TL as main agent with full bootstrap), `.claude/agents/*.md` (one per roster member), and `.claude/settings.local.json`
- The TL is auto-detected from the roster by role ("Tech Lead")
- After provisioning, the user starts a new Claude Code session and the TL loads automatically via CLAUDE.md
- An **install script** places the seed file and confirms credentials are configured

## Capabilities

### New Capabilities
- `seed-agent`: Global seed agent file that provisions a team onto a project via the TeamForge API
- `install-script`: One-time install script that places the seed agent file and verifies prerequisites

### Modified Capabilities
None.

## Impact

- **Files created per project**: CLAUDE.md, .claude/agents/*.md (one per agent), .claude/settings.local.json
- **Global files**: ~/.config/teamforge/seed.md (one-time install)
- **API**: No changes -- uses existing GET /api/v1/teams/{slug} and GET /api/v1/orgs/{slug} endpoints
- **Dependencies**: Requires credentials file at ~/.config/teamforge/credentials.json and gcloud auth
- **Long-term**: The file generation templates become reusable building blocks for the Wave 4 management console
