#!/usr/bin/env python3
"""
Migrate Nautilus team experience data from markdown files into TeamForge database.

Reads experience entries from ~/workspace/ai-teams/teams/nautilus/experience/
and POSTs them to the TeamForge experience API via batch endpoint.

Usage:
    python scripts/migrate_experience.py [--dry-run]
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

# === Constants ===

EXPERIENCE_DIR = Path.home() / "workspace" / "ai-teams" / "teams" / "nautilus" / "experience"
CREDENTIALS_PATH = Path.home() / ".config" / "teamforge" / "credentials.json"

# Agent UUID mapping (from Nautilus roster)
AGENT_MAP = {
    "dante": "26405c2b-698f-438e-be7d-1ce2bb99b066",
    "tl": "26405c2b-698f-438e-be7d-1ce2bb99b066",
    "quinn": "c7c57451-e0c2-4f2a-a02d-47e63575400f",
    "historian": "c7c57451-e0c2-4f2a-a02d-47e63575400f",
    "maya": "47ef9fec-f5fe-4ff4-8644-318cbcbc82c0",
    "ra": "47ef9fec-f5fe-4ff4-8644-318cbcbc82c0",
    "lena": "9df08aa3-eb0f-444a-86b4-20bebb046dfd",
    "ux": "9df08aa3-eb0f-444a-86b4-20bebb046dfd",
    "ux designer": "9df08aa3-eb0f-444a-86b4-20bebb046dfd",
    "nadia": "1266fdea-904c-41a0-be2d-8ed4019c3902",
    "pm": "1266fdea-904c-41a0-be2d-8ed4019c3902",
    "frank": "cded34a5-ce40-476b-a3d4-293e9cf92dba",
    "qa": "cded34a5-ce40-476b-a3d4-293e9cf92dba",
    "chris": "b59d5ddd-321e-4f29-80ac-bb5ba7212229",
    "dev": "b59d5ddd-321e-4f29-80ac-bb5ba7212229",
    "developer": "b59d5ddd-321e-4f29-80ac-bb5ba7212229",
}

# Default agent for ambiguous attribution
DEFAULT_AGENT_ID = AGENT_MAP["quinn"]

# Team and org IDs
TEAM_ID = "77df49cb-50cc-4a92-8b17-63887a9aa41a"
ORG_ID = "2e9aad24-e6a4-4a67-ae82-c1f7363b3749"

BATCH_SIZE = 50


# === Credential & Auth ===

def load_credentials():
    """Load API credentials from credentials file."""
    if not CREDENTIALS_PATH.exists():
        print(f"ERROR: Credentials file not found at {CREDENTIALS_PATH}")
        sys.exit(1)
    with open(CREDENTIALS_PATH) as f:
        creds = json.load(f)
    return creds["api_url"], creds["api_key"]


def get_gcp_token():
    """Get GCP identity token for Cloud Run auth."""
    try:
        result = subprocess.run(
            ["gcloud", "auth", "print-identity-token"],
            capture_output=True, text=True, check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        print("ERROR: Failed to get GCP identity token. Run 'gcloud auth login' first.")
        sys.exit(1)


# === Markdown Parsing ===

def split_sections(text):
    """Split markdown text on ## headings. Returns list of (title, body) tuples."""
    sections = []
    # Split on ## but not ### or deeper
    parts = re.split(r'^## ', text, flags=re.MULTILINE)
    for part in parts[1:]:  # Skip content before first ##
        lines = part.strip().split('\n', 1)
        title = lines[0].strip()
        body = lines[1].strip() if len(lines) > 1 else ""
        if title:
            sections.append((title, body))
    return sections


def resolve_agent(text):
    """Extract agent UUID from text containing 'Captured by' or similar attribution."""
    # Look for "Captured by: Agent" or "Captured by:** Agent"
    patterns = [
        r'\*\*Captured by:\*\*\s*(\w[\w\s]*?)(?:\s*\||\s*$)',
        r'Captured by:\s*(\w[\w\s]*?)(?:\s*\||\s*$)',
        r'\*\*Author:\*\*\s*(\w[\w\s]*?)(?:\s*$)',
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.MULTILINE)
        if match:
            agent_str = match.group(1).strip().rstrip('*').strip()
            # Try to match against known agents
            agent_lower = agent_str.lower()
            # Check for direct match
            if agent_lower in AGENT_MAP:
                return AGENT_MAP[agent_lower]
            # Check for partial match (e.g., "Dante (TL)")
            for key, uuid in AGENT_MAP.items():
                if key in agent_lower:
                    return uuid
            # Check for role in parens, e.g., "Quinn (Historian)"
            paren_match = re.search(r'\((\w+)\)', agent_str)
            if paren_match:
                role = paren_match.group(1).lower()
                if role in AGENT_MAP:
                    return AGENT_MAP[role]
    return DEFAULT_AGENT_ID


def parse_standard_file(filepath, observation_type):
    """Parse a standard experience file (lessons, patterns, heuristics, process_gaps)."""
    text = filepath.read_text()
    sections = split_sections(text)
    entries = []
    for title, body in sections:
        agent_id = resolve_agent(body)
        entries.append({
            "agent_id": agent_id,
            "team_id": TEAM_ID,
            "observation_type": observation_type,
            "title": title,
            "body": f"## {title}\n\n{body}",
            "scope": "team",
            "tags": [observation_type],
            "source_ref": filepath.name,
        })
    return entries


def parse_relationship_history(filepath):
    """Parse relationship_history.md into separate dated entries."""
    text = filepath.read_text()
    sections = split_sections(text)
    entries = []
    for title, body in sections:
        # Skip the horizontal rule sections that are just separators
        if not body.strip() or body.strip() == "---":
            continue
        agent_id = resolve_agent(body)
        entries.append({
            "agent_id": agent_id,
            "team_id": TEAM_ID,
            "observation_type": "relationship_note",
            "title": title,
            "body": f"## {title}\n\n{body}",
            "scope": "team",
            "tags": ["relationship_note"],
            "source_ref": filepath.name,
        })
    return entries


def parse_staging(filepath):
    """Parse staging.md -- only unpromoted entries (2026-03-15 TeamForge session)."""
    text = filepath.read_text()
    entries = []

    # Find unpromoted entries: they start with **date | Agent (Role) | context**
    # followed immediately by body text on the next line.
    # Match until the next entry header or end of file.
    unpromoted_pattern = r'\*\*(\d{4}-\d{2}-\d{2})\s*\|\s*(.*?)\s*\|\s*(.*?)\*\*\n(.*?)(?=\n\*\*\d{4}-\d{2}-\d{2}\s*\||\Z)'
    matches = re.findall(unpromoted_pattern, text, re.DOTALL)

    for date, agent_str, context, body in matches:
        body_text = body.strip()
        if not body_text:
            continue

        agent_str_clean = agent_str.strip()
        agent_id = DEFAULT_AGENT_ID

        # Check for role in parens first, e.g., "Maya (RA)"
        paren_match = re.search(r'\((\w+)\)', agent_str_clean)
        if paren_match:
            role = paren_match.group(1).lower()
            if role in AGENT_MAP:
                agent_id = AGENT_MAP[role]

        # Also check name directly
        if agent_id == DEFAULT_AGENT_ID:
            name = agent_str_clean.split('(')[0].strip().lower()
            if name in AGENT_MAP:
                agent_id = AGENT_MAP[name]

        title = f"Staging: {agent_str_clean} -- {context.strip()} ({date})"
        entries.append({
            "agent_id": agent_id,
            "team_id": TEAM_ID,
            "observation_type": "observation",
            "title": title,
            "body": body_text,
            "scope": "team",
            "tags": ["staging", "observation"],
            "source_ref": "staging.md",
        })

    return entries


def parse_retro(filepath):
    """Parse retrospective as a single observation entry."""
    text = filepath.read_text()
    return [{
        "agent_id": AGENT_MAP["quinn"],  # Quinn authored the retro
        "team_id": TEAM_ID,
        "observation_type": "observation",
        "title": "Retrospective: Bookmark Manager Project",
        "body": text,
        "scope": "team",
        "tags": ["retrospective", "observation"],
        "source_ref": "retros/bookmark-manager-retro.md",
    }]


# === API Operations ===

def make_headers(api_key, token):
    """Build request headers."""
    return {
        "X-API-Key": api_key,
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


def api_request(method, url, headers, data=None):
    """Make an API request via curl (avoids adding requests dependency)."""
    cmd = ["curl", "-s", "-X", method, "-w", "\n%{http_code}"]
    for k, v in headers.items():
        cmd.extend(["-H", f"{k}: {v}"])
    if data:
        cmd.extend(["-d", json.dumps(data)])
    cmd.append(url)

    result = subprocess.run(cmd, capture_output=True, text=True)
    output = result.stdout.strip()

    # Split response body and status code
    lines = output.rsplit('\n', 1)
    if len(lines) == 2:
        body_str, status_code = lines
    else:
        body_str = output
        status_code = "0"

    try:
        body = json.loads(body_str) if body_str else {}
    except json.JSONDecodeError:
        body = {"raw": body_str}

    return int(status_code), body


def get_existing_titles(api_url, headers, agent_id):
    """Get existing entry titles for an agent to check for duplicates."""
    titles = set()
    offset = 0
    limit = 20  # API max per request
    while True:
        url = f"{api_url}/api/v1/agents/{agent_id}/experience?offset={offset}&limit={limit}"
        status, data = api_request("GET", url, headers)
        if status != 200 or not data.get("entries"):
            break
        for entry in data["entries"]:
            if entry.get("title"):
                titles.add(entry["title"])
        total = data.get("total", 0)
        offset += limit
        if offset >= total:
            break
    return titles


def submit_batch(api_url, headers, entries):
    """Submit a batch of entries to the experience API."""
    url = f"{api_url}/api/v1/experience/batch"
    payload = {"entries": entries}
    status, data = api_request("POST", url, headers, payload)
    return status, data


def search_experience(api_url, headers, query, agent_id):
    """Run a semantic search query."""
    url = f"{api_url}/api/v1/experience/search"
    payload = {
        "query": query,
        "filters": {"agent_id": agent_id, "team_id": TEAM_ID},
        "limit": 5,
    }
    status, data = api_request("POST", url, headers, payload)
    return status, data


# === Main ===

def main():
    dry_run = "--dry-run" in sys.argv

    print("=" * 60)
    print("TeamForge Experience Migration")
    print("=" * 60)

    if dry_run:
        print(">>> DRY RUN MODE -- no data will be written <<<\n")

    # Load credentials
    api_url, api_key = load_credentials()
    print(f"API: {api_url}")

    # Get GCP token
    if not dry_run:
        token = get_gcp_token()
        headers = make_headers(api_key, token)
    else:
        headers = {}

    # Parse all files
    print(f"\nSource: {EXPERIENCE_DIR}")
    print("-" * 40)

    all_entries = []

    # 1. Lessons learned
    filepath = EXPERIENCE_DIR / "lessons_learned.md"
    entries = parse_standard_file(filepath, "lesson")
    print(f"  lessons_learned.md:     {len(entries)} entries")
    all_entries.extend(entries)

    # 2. Successful patterns
    filepath = EXPERIENCE_DIR / "successful_patterns.md"
    entries = parse_standard_file(filepath, "pattern")
    print(f"  successful_patterns.md: {len(entries)} entries")
    all_entries.extend(entries)

    # 3. Prior failures (process gaps)
    filepath = EXPERIENCE_DIR / "prior_failures.md"
    entries = parse_standard_file(filepath, "process_gap")
    print(f"  prior_failures.md:      {len(entries)} entries")
    all_entries.extend(entries)

    # 4. Team heuristics
    filepath = EXPERIENCE_DIR / "team_heuristics.md"
    entries = parse_standard_file(filepath, "heuristic")
    print(f"  team_heuristics.md:     {len(entries)} entries")
    all_entries.extend(entries)

    # 5. Relationship history
    filepath = EXPERIENCE_DIR / "relationship_history.md"
    entries = parse_relationship_history(filepath)
    print(f"  relationship_history.md: {len(entries)} entries")
    all_entries.extend(entries)

    # 6. Staging (unpromoted only)
    filepath = EXPERIENCE_DIR / "staging.md"
    entries = parse_staging(filepath)
    print(f"  staging.md (unpromoted): {len(entries)} entries")
    all_entries.extend(entries)

    # 7. Retrospective
    retro_path = EXPERIENCE_DIR / "retros" / "bookmark-manager-retro.md"
    entries = parse_retro(retro_path)
    print(f"  bookmark-manager-retro:  {len(entries)} entries")
    all_entries.extend(entries)

    print(f"\n  TOTAL PARSED: {len(all_entries)} entries")

    if dry_run:
        print("\n--- Dry Run Summary ---")
        by_type = {}
        for e in all_entries:
            by_type.setdefault(e["observation_type"], []).append(e)
        for obs_type, entries in sorted(by_type.items()):
            print(f"  {obs_type}: {len(entries)}")
            for e in entries:
                agent_name = "unknown"
                for name, uuid in AGENT_MAP.items():
                    if uuid == e["agent_id"] and len(name) > 2:
                        agent_name = name
                        break
                print(f"    - [{agent_name}] {e['title'][:70]}")
        print("\nDry run complete. Remove --dry-run to execute migration.")
        return

    # Idempotency check: get existing titles per agent
    print("\nChecking for existing entries...")
    agent_ids = set(e["agent_id"] for e in all_entries)
    existing_titles_by_agent = {}
    for agent_id in agent_ids:
        existing_titles_by_agent[agent_id] = get_existing_titles(api_url, headers, agent_id)
        count = len(existing_titles_by_agent[agent_id])
        if count > 0:
            print(f"  Agent {agent_id[:8]}...: {count} existing entries")

    # Filter out duplicates
    new_entries = []
    skipped = 0
    for entry in all_entries:
        existing = existing_titles_by_agent.get(entry["agent_id"], set())
        if entry["title"] in existing:
            skipped += 1
        else:
            new_entries.append(entry)

    print(f"\n  New entries to create: {len(new_entries)}")
    print(f"  Skipped (duplicates):  {skipped}")

    if not new_entries:
        print("\nNo new entries to migrate. Migration is already complete.")
        # Still run validation
    else:
        # Submit in batches
        print(f"\nSubmitting in batches of {BATCH_SIZE}...")
        created = 0
        failed = 0
        for i in range(0, len(new_entries), BATCH_SIZE):
            batch = new_entries[i:i + BATCH_SIZE]
            batch_num = (i // BATCH_SIZE) + 1
            total_batches = (len(new_entries) + BATCH_SIZE - 1) // BATCH_SIZE
            print(f"  Batch {batch_num}/{total_batches} ({len(batch)} entries)...", end=" ")

            status, data = submit_batch(api_url, headers, batch)
            if status == 201:
                created += len(batch)
                print(f"OK ({len(batch)} created)")
            else:
                failed += len(batch)
                print(f"FAILED (HTTP {status})")
                print(f"    Error: {json.dumps(data)[:200]}")

        print(f"\n  Created: {created}")
        print(f"  Failed:  {failed}")

    # Validation
    print("\n" + "=" * 60)
    print("Validation")
    print("=" * 60)

    # Count validation -- check a few agents
    total_in_db = 0
    for agent_id in agent_ids:
        titles = get_existing_titles(api_url, headers, agent_id)
        total_in_db += len(titles)
    print(f"\n  Total entries in DB (across migrated agents): {total_in_db}")
    print(f"  Expected (parsed):                            {len(all_entries)}")
    if total_in_db >= len(all_entries):
        print("  Count validation: PASS")
    else:
        print(f"  Count validation: WARN (DB has {total_in_db}, expected >= {len(all_entries)})")

    # Semantic search validation
    print("\n  Semantic search: 'What did the team learn about UX involvement?'")
    # Use Dante's ID for the search (he can see team-scoped entries)
    status, data = search_experience(
        api_url, headers,
        "What did the team learn about UX involvement?",
        AGENT_MAP["dante"]
    )
    if status == 200 and data.get("results"):
        results = data["results"]
        print(f"  Results returned: {len(results)}")
        for r in results[:3]:
            sim = r.get("similarity", 0)
            title = r.get("title", "untitled")[:60]
            print(f"    {sim:.4f} -- {title}")
        top_sim = results[0].get("similarity", 0)
        if top_sim > 0.5:
            print(f"  Search validation: PASS (top similarity: {top_sim:.4f})")
        else:
            print(f"  Search validation: WARN (top similarity {top_sim:.4f} < 0.5)")
    else:
        print(f"  Search validation: FAIL (HTTP {status})")
        if data:
            print(f"    Response: {json.dumps(data)[:200]}")

    print("\n" + "=" * 60)
    print("Migration complete.")
    print("=" * 60)


if __name__ == "__main__":
    main()
