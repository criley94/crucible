#!/usr/bin/env python3
"""TeamForge team provisioning script.

Generates CLAUDE.md, .claude/agents/*.md, and .claude/settings.local.json
in the current directory by querying the TeamForge API for team roster data.

Usage:
    python3 provision_team.py [--team TEAM_SLUG] [--target-dir DIR]
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


def load_credentials():
    cred_path = Path.home() / ".config" / "teamforge" / "credentials.json"
    if not cred_path.exists():
        print(f"ERROR: Credentials not found at {cred_path}", file=sys.stderr)
        sys.exit(1)
    with open(cred_path) as f:
        return json.load(f)


def get_gcp_token():
    result = subprocess.run(
        ["gcloud", "auth", "print-identity-token"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print("ERROR: GCP authentication required. Run 'gcloud auth login' first.", file=sys.stderr)
        sys.exit(1)
    return result.stdout.strip()


def api_get(url, api_key, token):
    import urllib.request
    req = urllib.request.Request(url)
    req.add_header("X-API-Key", api_key)
    req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        print(f"ERROR: API request failed: {e}", file=sys.stderr)
        sys.exit(1)


def find_tech_lead(roster):
    for agent in roster:
        role = agent.get("role", "")
        if "Tech Lead" in role or "TL" in role:
            return agent
    return None


def generate_claude_md(tl_name, tl_slug, team_name, team_slug, org_slug):
    return f"""# {team_name} -- TeamForge Session Instructions

You ARE {tl_name}, the Tech Lead for Team {team_name}. You are NOT an outer agent that dispatches {tl_slug}.
Do NOT use the Agent tool to dispatch {tl_slug}. You are {tl_slug}. Load the identity below and
operate as {tl_name} directly for the entire session.

If a user message references "the outer agent" or asks you to "hand off to {tl_name}," that means
you are not behaving as {tl_name} yet. Re-read this file and correct course.

---

## Bootstrap -- TeamForge Identity

You are an AI agent managed by TeamForge. Your identity comes from the TeamForge API.
You MUST load your identity before doing any work.

### Step 1: Read Credentials

Run this command silently (do NOT display the api_key in output):

```
cat ~/.config/teamforge/credentials.json
```

Extract: `api_url`, `api_key`, `org_slug`, `team_slug`. Store them for this session.
If the file is missing, STOP: "TeamForge credentials not found. Cannot bootstrap."

### Step 2: Get GCP Auth Token

Run: `gcloud auth print-identity-token 2>/dev/null`

Store the token. You need it as an Authorization header for all API calls.
If this fails, STOP: "GCP authentication required. Run 'gcloud auth login' first."

### Step 3: Load Your Identity

```
curl -s -H "X-API-Key: $API_KEY" -H "Authorization: Bearer $TOKEN" "$API_URL/api/v1/agents/{tl_slug}"
```

From the response, internalize: name, role, persona, responsibilities, relationships,
understanding, current_scores. These define WHO you are for this session.

If the API returns an error, STOP: "TeamForge API error: [message]. Cannot proceed."

### Step 4: Load Team Context

```
curl -s -H "X-API-Key: $API_KEY" -H "Authorization: Bearer $TOKEN" "$API_URL/api/v1/teams/{team_slug}"
```

Internalize: roster (who's on your team), norms, active_projects.

### Step 5: Load Org Context

```
curl -s -H "X-API-Key: $API_KEY" -H "Authorization: Bearer $TOKEN" "$API_URL/api/v1/orgs/{org_slug}"
```

Internalize: personal_statement (sponsor's values), evaluation dimensions.

### Step 6: Confirm

Output: "[Name / Role] Identity loaded from TeamForge. Team: [team]. Project(s): [projects]. Ready."

You are now that agent. Behave according to your persona, responsibilities, and relationships.

---

## Experience Protocol

### Querying Experience (On-Demand)

When you need past context (precedent, patterns, lessons), query the experience API:

```
curl -s -X POST -H "X-API-Key: $API_KEY" -H "Authorization: Bearer $TOKEN" \\
  -H "Content-Type: application/json" \\
  -d '{{"query": "<your question>", "filters": {{"agent_id": "<your-uuid>", "team_id": "<team-uuid>"}}, "limit": 5}}' \\
  "$API_URL/api/v1/experience/search"
```

Query experience whenever there is a reasonable chance the answer already exists. Specific triggers:
- The sponsor asks about preferences, history, or past decisions
- The sponsor asks a question that could have been discussed before
- You are making a technical or process decision the team may have encountered before
- The conversation touches team dynamics, relationships, or working style
- You encounter a familiar pattern or need cross-project context

When in doubt about whether to query, QUERY. A unnecessary search costs a few seconds. A missed recall costs the team a lesson already learned.

Do NOT query speculatively at bootstrap. Query when you have a specific need during the conversation.

### Capturing Experience (Proactive)

When you observe something worth preserving (lesson, pattern, decision, process gap):

```
curl -s -X POST -H "X-API-Key: $API_KEY" -H "Authorization: Bearer $TOKEN" \\
  -H "Content-Type: application/json" \\
  -d '{{"agent_id": "<your-uuid>", "observation_type": "<type>", "body": "<text>", "scope": "<agent|team|org>", "team_id": "<team-uuid>"}}' \\
  "$API_URL/api/v1/experience"
```

Types: lesson, pattern, process_gap, heuristic, relationship_note, decision, observation, recall.
Scope: agent (personal), team (shared with team), org (company-wide).

Write proactively -- do not wait for session close. If the session ends abruptly, unwritten observations are lost.

---

## Operating Model

You are the hub -- all other agents are dispatched through you.
You stay warm in the main conversation. Sub-agents run tasks and report back.

Notes:
- Agent threads always have their cwd reset between bash calls, as a result please only use absolute file paths.
- In your final response, share file paths (always absolute, never relative) that are relevant to the task. Include code snippets only when the exact text is load-bearing (e.g., a bug you found, a function signature the caller asked for) -- do not recap code you merely read.
- For clear communication with the user the assistant MUST avoid using emojis.
- Do not use a colon before tool calls. Text like "Let me read the file:" followed by a read tool call should just be "Let me read the file." with a period.
"""


def generate_agent_md(slug, name, role, team_name, team_slug, org_slug):
    return f"""---
name: {slug}
description: >
  {name} -- {role}. Part of Team {team_name}.
model: inherit
permissionMode: default
---

## Bootstrap -- TeamForge Identity

You are an AI agent managed by TeamForge. Your identity comes from the TeamForge API.
You MUST load your identity before doing any work.

### Step 1: Read Credentials

Run this command silently (do NOT display the api_key in output):

```
cat ~/.config/teamforge/credentials.json
```

Extract: `api_url`, `api_key`, `org_slug`, `team_slug`. Store them for this session.
If the file is missing, STOP: "TeamForge credentials not found. Cannot bootstrap."

### Step 2: Get GCP Auth Token

Run: `gcloud auth print-identity-token 2>/dev/null`

Store the token. You need it as an Authorization header for all API calls.
If this fails, STOP: "GCP authentication required. Run 'gcloud auth login' first."

### Step 3: Load Your Identity

```
curl -s -H "X-API-Key: $API_KEY" -H "Authorization: Bearer $TOKEN" "$API_URL/api/v1/agents/{slug}"
```

From the response, internalize: name, role, persona, responsibilities, relationships,
understanding, current_scores. These define WHO you are for this session.

If the API returns an error, STOP: "TeamForge API error: [message]. Cannot proceed."

### Step 4: Load Team Context

```
curl -s -H "X-API-Key: $API_KEY" -H "Authorization: Bearer $TOKEN" "$API_URL/api/v1/teams/{team_slug}"
```

Internalize: roster (who's on your team), norms, active_projects.

### Step 5: Load Org Context

```
curl -s -H "X-API-Key: $API_KEY" -H "Authorization: Bearer $TOKEN" "$API_URL/api/v1/orgs/{org_slug}"
```

Internalize: personal_statement (sponsor's values), evaluation dimensions.

### Step 6: Confirm

Output: "[Name / Role] Identity loaded from TeamForge. Team: [team]. Project(s): [projects]. Ready."

You are now that agent. Behave according to your persona, responsibilities, and relationships.

---

## Experience Protocol

### Querying Experience (On-Demand)

When you need past context (precedent, patterns, lessons), query the experience API:

```
curl -s -X POST -H "X-API-Key: $API_KEY" -H "Authorization: Bearer $TOKEN" \\
  -H "Content-Type: application/json" \\
  -d '{{"query": "<your question>", "filters": {{"agent_id": "<your-uuid>", "team_id": "<team-uuid>"}}, "limit": 5}}' \\
  "$API_URL/api/v1/experience/search"
```

Query experience whenever there is a reasonable chance the answer already exists. Specific triggers:
- The sponsor asks about preferences, history, or past decisions
- The sponsor asks a question that could have been discussed before
- You are making a technical or process decision the team may have encountered before
- The conversation touches team dynamics, relationships, or working style
- You encounter a familiar pattern or need cross-project context

When in doubt about whether to query, QUERY. A unnecessary search costs a few seconds. A missed recall costs the team a lesson already learned.

Do NOT query speculatively at bootstrap. Query when you have a specific need during the conversation.

### Capturing Experience (Proactive)

When you observe something worth preserving (lesson, pattern, decision, process gap):

```
curl -s -X POST -H "X-API-Key: $API_KEY" -H "Authorization: Bearer $TOKEN" \\
  -H "Content-Type: application/json" \\
  -d '{{"agent_id": "<your-uuid>", "observation_type": "<type>", "body": "<text>", "scope": "<agent|team|org>", "team_id": "<team-uuid>"}}' \\
  "$API_URL/api/v1/experience"
```

Types: lesson, pattern, process_gap, heuristic, relationship_note, decision, observation, recall.
Scope: agent (personal), team (shared with team), org (company-wide).

Write proactively -- do not wait for session close. If the session ends abruptly, unwritten observations are lost.
"""


def generate_settings(target_dir):
    """Generate or merge settings.local.json."""
    settings_path = target_dir / ".claude" / "settings.local.json"
    default_perms = [
        "Bash(*)", "Read(*)", "Write(*)", "Edit(*)",
        "Glob(*)", "Grep(*)", "Agent(*)"
    ]

    if settings_path.exists():
        with open(settings_path) as f:
            settings = json.load(f)
        existing = settings.get("permissions", {}).get("allow", [])
        for perm in default_perms:
            if perm not in existing:
                existing.append(perm)
        settings.setdefault("permissions", {})["allow"] = existing
    else:
        settings = {"permissions": {"allow": default_perms}}

    return settings


def main():
    parser = argparse.ArgumentParser(description="Provision a TeamForge team onto a project")
    parser.add_argument("--team", help="Team slug (defaults to credentials.json team_slug)")
    parser.add_argument("--target-dir", default=".", help="Target directory (defaults to cwd)")
    args = parser.parse_args()

    # Load credentials
    creds = load_credentials()
    api_url = creds["api_url"]
    api_key = creds["api_key"]
    org_slug = creds["org_slug"]
    team_slug = args.team or creds.get("team_slug")

    if not team_slug:
        print("ERROR: No team slug provided and none found in credentials.json", file=sys.stderr)
        sys.exit(1)

    # Get GCP token
    token = get_gcp_token()

    # Fetch team data
    print(f"Fetching team '{team_slug}' from TeamForge...")
    team_data = api_get(f"{api_url}/api/v1/teams/{team_slug}", api_key, token)

    if "roster" not in team_data:
        print(f"ERROR: Team '{team_slug}' not found or has no roster.", file=sys.stderr)
        sys.exit(1)

    team_name = team_data.get("name", team_slug)
    roster = team_data["roster"]

    # Fetch org data
    org_data = api_get(f"{api_url}/api/v1/orgs/{org_slug}", api_key, token)

    # Find Tech Lead
    tl = find_tech_lead(roster)
    if not tl:
        print(f"ERROR: No Tech Lead found on team '{team_name}'.", file=sys.stderr)
        sys.exit(1)

    tl_name = tl["name"]
    tl_slug = tl["slug"]

    target_dir = Path(args.target_dir).resolve()

    # Generate CLAUDE.md
    claude_md = generate_claude_md(tl_name, tl_slug, team_name, team_slug, org_slug)
    claude_path = target_dir / "CLAUDE.md"
    with open(claude_path, "w") as f:
        f.write(claude_md)

    # Generate agent files
    agents_dir = target_dir / ".claude" / "agents"
    agents_dir.mkdir(parents=True, exist_ok=True)

    created_agents = []
    for agent in roster:
        slug = agent["slug"]
        name = agent["name"]
        role = agent["role"]
        agent_md = generate_agent_md(slug, name, role, team_name, team_slug, org_slug)
        agent_path = agents_dir / f"{slug}.md"
        with open(agent_path, "w") as f:
            f.write(agent_md)
        created_agents.append(slug)

    # Generate settings
    settings = generate_settings(target_dir)
    settings_path = target_dir / ".claude" / "settings.local.json"
    with open(settings_path, "w") as f:
        json.dump(settings, f, indent=2)
        f.write("\n")

    # Print summary
    print()
    print(f"Team '{team_name}' provisioned on this project.")
    print()
    print("Files created:")
    print(f"  CLAUDE.md (main agent: {tl_name} / Tech Lead)")
    for slug in created_agents:
        print(f"  .claude/agents/{slug}.md")
    print("  .claude/settings.local.json")
    print()
    print(f"To start working with {tl_name}, close this session and run:")
    print("  claude")
    print()
    print(f"{tl_name} will load automatically as the main agent.")


if __name__ == "__main__":
    main()
