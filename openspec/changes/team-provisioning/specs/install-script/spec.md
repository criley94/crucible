## ADDED Requirements

### Requirement: Install script places seed agent file
The install script SHALL copy the seed agent file to `~/.config/teamforge/seed.md`. If `~/.config/teamforge/` does not exist, it SHALL create the directory.

#### Scenario: Fresh install
- **WHEN** `~/.config/teamforge/seed.md` does not exist
- **THEN** the script SHALL create it and confirm: "Seed agent installed at ~/.config/teamforge/seed.md"

#### Scenario: Update existing
- **WHEN** `~/.config/teamforge/seed.md` already exists
- **THEN** the script SHALL overwrite it and confirm: "Seed agent updated at ~/.config/teamforge/seed.md"

### Requirement: Install script verifies prerequisites
The install script SHALL check that `~/.config/teamforge/credentials.json` exists and that `gcloud` is available on PATH. It SHALL warn (not fail) if either is missing.

#### Scenario: All prerequisites met
- **WHEN** credentials exist and gcloud is available
- **THEN** the script SHALL print: "Prerequisites OK"

#### Scenario: Credentials missing
- **WHEN** credentials file does not exist
- **THEN** the script SHALL warn: "WARNING: credentials.json not found. Create it before using the seed agent."

### Requirement: Install script prints usage
After installation, the script SHALL print usage instructions showing how to provision a team on a new project.

#### Scenario: Usage printed
- **WHEN** installation completes
- **THEN** the script SHALL print the command: "claude --agent ~/.config/teamforge/seed.md"
