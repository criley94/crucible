## ADDED Requirements

### Requirement: Parse markdown experience files into structured entries
The migration script SHALL parse each of the 7 Nautilus experience markdown files and extract individual entries by splitting on `## ` section headings. Each entry SHALL have a title (from the heading), a body (the section content), and metadata extracted from the content (captured-by agent, date, source).

#### Scenario: Parse lessons_learned.md
- **WHEN** the script processes `lessons_learned.md`
- **THEN** it SHALL extract 24 entries (L1 through L24), each with observation_type "lesson"

#### Scenario: Parse successful_patterns.md
- **WHEN** the script processes `successful_patterns.md`
- **THEN** it SHALL extract 14 entries (P1 through P14), each with observation_type "pattern"

#### Scenario: Parse prior_failures.md
- **WHEN** the script processes `prior_failures.md`
- **THEN** it SHALL extract 7 entries (FL1 through FL7), each with observation_type "process_gap"

#### Scenario: Parse team_heuristics.md
- **WHEN** the script processes `team_heuristics.md`
- **THEN** it SHALL extract 13 entries (H1 through H13), each with observation_type "heuristic"

#### Scenario: Parse relationship_history.md
- **WHEN** the script processes `relationship_history.md`
- **THEN** it SHALL extract each dated section as a separate entry with observation_type "relationship_note"

#### Scenario: Parse staging.md -- unpromoted entries only
- **WHEN** the script processes `staging.md`
- **THEN** it SHALL extract only the 4 unpromoted entries dated 2026-03-15 (TeamForge session observations), each with observation_type "observation"
- **AND** it SHALL skip all promoted entries (marked with `*Promoted*` blocks)

#### Scenario: Parse retros/bookmark-manager-retro.md
- **WHEN** the script processes the retrospective file
- **THEN** it SHALL create a single entry with observation_type "observation" and title "Retrospective: Bookmark Manager Project"

### Requirement: Attribute entries to correct agents
The migration script SHALL map each entry's "Captured by" field to the correct agent UUID from the Nautilus roster. The script SHALL support mappings for all 7 attributable agents (Dante/TL, Quinn/Historian, Maya/RA, Lena/UX, Nadia/PM, Frank/QA, Chris/Dev). If attribution is ambiguous or missing, the script SHALL default to Quinn (Historian).

#### Scenario: Entry captured by TL
- **WHEN** an entry's "Captured by" field contains "TL" or "Dante"
- **THEN** the entry's agent_id SHALL be set to Dante's UUID

#### Scenario: Entry with ambiguous attribution
- **WHEN** an entry has no "Captured by" field or the attribution cannot be resolved
- **THEN** the entry's agent_id SHALL default to Quinn's UUID

### Requirement: Set correct scope and team context
All migrated entries SHALL have `scope: "team"` and `team_id` set to the Nautilus team UUID. The `org_id` SHALL be set to the Hands-On Analytics org UUID.

#### Scenario: All entries are team-scoped
- **WHEN** any entry is migrated
- **THEN** its scope SHALL be "team", its team_id SHALL be the Nautilus team UUID, and its org_id SHALL be the Hands-On Analytics org UUID

### Requirement: Idempotent migration
The migration script SHALL check for existing entries before inserting. If an entry with the same title already exists for the same agent, the script SHALL skip it and report it as a duplicate.

#### Scenario: First run creates all entries
- **WHEN** the script runs against an empty experience database
- **THEN** all parsed entries SHALL be created successfully

#### Scenario: Re-run skips duplicates
- **WHEN** the script runs after a previous successful migration
- **THEN** no duplicate entries SHALL be created
- **AND** the script SHALL report how many entries were skipped

### Requirement: Batch API submission
The migration script SHALL submit entries via `POST /api/v1/experience/batch` in batches of up to 50 entries. The script SHALL read API credentials from `~/.config/teamforge/credentials.json` and obtain a GCP identity token via `gcloud auth print-identity-token`.

#### Scenario: Entries submitted in batches
- **WHEN** there are more than 50 entries to migrate
- **THEN** the script SHALL split them into batches of 50 and submit sequentially

#### Scenario: Batch failure is reported
- **WHEN** a batch submission fails
- **THEN** the script SHALL report the error and the entries that failed
- **AND** the script SHALL continue with remaining batches

### Requirement: Post-migration validation
After all entries are submitted, the script SHALL validate the migration by: (1) counting total entries in the database for the Nautilus team, (2) running a semantic search query to verify embeddings are functional.

#### Scenario: Count validation
- **WHEN** migration completes
- **THEN** the script SHALL query the API for total entry count and report expected vs. actual

#### Scenario: Semantic search validation
- **WHEN** migration completes
- **THEN** the script SHALL run a semantic search for "What did the team learn about UX involvement?" and verify that relevant results are returned with similarity > 0.5
