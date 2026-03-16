## ADDED Requirements

### Requirement: Seed agent reads credentials and authenticates
The seed agent SHALL read `~/.config/teamforge/credentials.json` to obtain `api_url`, `api_key`, `org_slug`, and `team_slug`. It SHALL obtain a GCP identity token via `gcloud auth print-identity-token`. If credentials are missing or auth fails, it SHALL stop with a clear error message.

#### Scenario: Credentials present and auth succeeds
- **WHEN** the seed agent is invoked and credentials exist and gcloud auth succeeds
- **THEN** it SHALL proceed to team discovery

#### Scenario: Credentials missing
- **WHEN** the seed agent is invoked and credentials file does not exist
- **THEN** it SHALL stop with: "TeamForge credentials not found at ~/.config/teamforge/credentials.json"

#### Scenario: GCP auth fails
- **WHEN** gcloud auth print-identity-token fails
- **THEN** it SHALL stop with: "GCP authentication required. Run 'gcloud auth login' first."

### Requirement: Seed agent discovers team and identifies TL
The seed agent SHALL use `team_slug` from credentials to query `GET /api/v1/teams/{slug}`. From the roster, it SHALL identify the Tech Lead by finding the agent with `role: "Tech Lead"`. If no Tech Lead exists on the roster, it SHALL stop with an error.

#### Scenario: Team found with TL on roster
- **WHEN** the API returns a team with a Tech Lead on the roster
- **THEN** the seed agent SHALL proceed to provisioning with that TL's slug as the primary agent

#### Scenario: Team not found
- **WHEN** the API returns 404 for the team slug
- **THEN** it SHALL stop with: "Team '{slug}' not found in TeamForge."

#### Scenario: No Tech Lead on roster
- **WHEN** the team roster has no agent with role "Tech Lead"
- **THEN** it SHALL stop with: "No Tech Lead found on team '{name}'. Cannot provision without a TL."

### Requirement: Seed agent generates CLAUDE.md
The seed agent SHALL create a `CLAUDE.md` file in the current project directory. The file SHALL contain:
1. An identity preamble declaring the TL as the main agent (by name and role)
2. The full TeamForge bootstrap sequence (credentials, GCP token, identity, team, org)
3. The experience protocol (query and capture)
4. A generic operating model section
5. Standard agent behavioral notes (absolute paths, no emojis, etc.)

The TL slug, team slug, and org slug SHALL be parameterized from the API response.

#### Scenario: CLAUDE.md created for Nautilus team
- **WHEN** provisioning team "nautilus" with TL "dante-tl"
- **THEN** CLAUDE.md SHALL reference "dante-tl" in bootstrap step 3 and "nautilus" in step 4

#### Scenario: CLAUDE.md does not exist yet
- **WHEN** no CLAUDE.md exists in the project
- **THEN** the seed agent SHALL create it

#### Scenario: CLAUDE.md already exists
- **WHEN** CLAUDE.md already exists in the project
- **THEN** the seed agent SHALL warn the user and ask whether to overwrite before proceeding

### Requirement: Seed agent generates agent definition files
The seed agent SHALL create `.claude/agents/{slug}.md` for every agent on the team roster. Each file SHALL contain:
1. YAML frontmatter with: name (slug), description (from API), model (inherit), permissionMode (default)
2. The full TeamForge bootstrap sequence parameterized with that agent's slug
3. The experience protocol
4. A role-appropriate operating model note

#### Scenario: All roster agents get definition files
- **WHEN** the team has 9 agents on the roster
- **THEN** 9 files SHALL be created in `.claude/agents/`

#### Scenario: Agent description comes from API
- **WHEN** an agent has a role and name in the API
- **THEN** the YAML description field SHALL include the agent's name, role, and a brief description derived from the API response

### Requirement: Seed agent generates settings file
The seed agent SHALL create `.claude/settings.local.json` with pre-approved tool permissions for common project operations (file reads, writes, bash commands for git and build tools).

#### Scenario: Settings file created
- **WHEN** provisioning completes
- **THEN** `.claude/settings.local.json` SHALL exist with reasonable default permissions

#### Scenario: Settings file already exists
- **WHEN** `.claude/settings.local.json` already exists
- **THEN** the seed agent SHALL preserve existing settings and only add missing entries

### Requirement: Seed agent reports completion
After provisioning, the seed agent SHALL report what was created and instruct the user to start a new session to talk to the TL.

#### Scenario: Provisioning complete
- **WHEN** all files are generated
- **THEN** the seed agent SHALL output: "Team '{name}' provisioned. Start a new Claude Code session to talk to [TL Name] ([TL Role])."
- **AND** it SHALL list all files created
