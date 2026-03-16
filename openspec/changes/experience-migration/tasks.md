## 1. Migration Script Core

- [x] 1.1 Create `scripts/migrate_experience.py` with CLI entry point, credential loading, and GCP token acquisition
- [x] 1.2 Implement markdown parser: split files on `## ` headings, extract title and body
- [x] 1.3 Implement attribution mapper: parse "Captured by" fields and map to agent UUIDs
- [x] 1.4 Implement file-specific parsers for each of the 7 source files with correct observation_type mapping
- [x] 1.5 Implement staging.md parser that skips promoted entries and only extracts unpromoted 2026-03-15 entries
- [x] 1.6 Implement retro parser that creates a single observation entry from the full retrospective

## 2. API Integration

- [x] 2.1 Implement idempotency check: query existing entries per agent and skip duplicates by title
- [x] 2.2 Implement batch submission: split entries into batches of 50, POST to `/api/v1/experience/batch`
- [x] 2.3 Add error handling: report failed batches, continue with remaining

## 3. Validation

- [x] 3.1 Implement count validation: compare expected entry count vs. actual from API
- [x] 3.2 Implement semantic search validation: query "What did the team learn about UX involvement?" and verify results
- [x] 3.3 Print migration summary: entries created, skipped, failed, and search validation result

## 4. Execute and Verify

- [x] 4.1 Run migration script against production API
- [x] 4.2 Verify entries are queryable via the experience search endpoint
- [x] 4.3 Run the Green Cheese Test equivalent: search for a specific lesson and confirm semantic match
