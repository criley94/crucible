# Proposal: Plain-Language Provisioning Scripts

**Author:** Maya (RA) -- retroactive documentation
**Date:** 2026-03-16
**Status:** Complete -- scripts implemented and operational
**Parent:** TeamForge Phase 1

---

## Problem Statement

After the seed agent (seed.md) was built for interactive provisioning, there was a need for programmatic provisioning that could be invoked without launching a Claude Code session. A user or another agent should be able to say "attach team nautilus to this project" and have the provisioning happen automatically.

---

## What Was Built

### provision_team.py

A standalone Python script that generates TeamForge configuration for any project directory.

**What it does:**
1. Reads credentials from `~/.config/teamforge/credentials.json`
2. Authenticates via GCP identity token (`gcloud auth print-identity-token`)
3. Fetches team roster from the TeamForge API
4. Auto-detects the Tech Lead by role
5. Generates `CLAUDE.md` with TL as the main session agent
6. Generates `.claude/agents/{slug}.md` for every roster member
7. Generates or merges `.claude/settings.local.json` with required permissions
8. Reports completion with file list and next steps

**Key features:**
- `--team TEAM_SLUG` argument (defaults to credentials.json team_slug)
- `--target-dir DIR` argument (defaults to current working directory)
- Settings merge: if settings.local.json exists, adds missing permissions without removing existing ones
- Uses only stdlib (no pip dependencies beyond what the API already requires)

### provision_team.sh

A bash wrapper that invokes `provision_team.py` with optional team slug argument. Installed alongside the Python script at `~/.config/teamforge/`.

### install_seed.sh

An install script that places the seed agent and provisioning scripts into `~/.config/teamforge/`. Checks prerequisites (credentials.json exists, gcloud available, claude CLI available) and prints usage instructions.

---

## Files

| File | Location | Purpose |
|------|----------|---------|
| provision_team.py | /home/cheston_riley/workspace/crucible/scripts/provision_team.py | Main provisioning script |
| provision_team.sh | /home/cheston_riley/workspace/crucible/scripts/provision_team.sh | Bash wrapper |
| install_seed.sh | /home/cheston_riley/workspace/crucible/scripts/install_seed.sh | Installs seed + scripts to ~/.config/teamforge/ |

---

## Relationship to Seed Agent

The seed agent (seed.md) and provision_team.py implement the same provisioning logic through different invocation paths:
- **seed.md**: Interactive. Launched as a Claude Code agent session. Queries the API, generates files, and reports to the user conversationally.
- **provision_team.py**: Programmatic. Run from the command line or by another script. Same output, no interactive session.

Both produce identical output files (CLAUDE.md, agent definitions, settings).

---

## Note

The provisioning scripts were built as part of the Wave 3.5 team-provisioning change. The seed agent is documented in the team-provisioning OpenSpec change. This proposal retroactively documents the standalone script variant, which was built alongside the seed agent but was not given its own OpenSpec entry.
