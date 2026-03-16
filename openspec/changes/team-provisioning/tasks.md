## 1. Seed Agent File

- [x] 1.1 Create `seed.md` with YAML frontmatter and credential/auth bootstrap section
- [x] 1.2 Add team discovery logic: read team_slug from credentials, query API, find TL by role
- [x] 1.3 Add CLAUDE.md generation template parameterized by TL slug, team slug, org slug
- [x] 1.4 Add agent definition file generation template (loop over roster, create .claude/agents/{slug}.md)
- [x] 1.5 Add settings.local.json generation with default permissions
- [x] 1.6 Add idempotency checks: warn if files exist, ask before overwriting
- [x] 1.7 Add completion report: list files created, instruct user to start new session

## 2. Install Script

- [x] 2.1 Create `scripts/install_seed.sh`: copy seed.md to ~/.config/teamforge/, verify prerequisites, print usage

## 3. Test and Verify

- [x] 3.1 Run install script to place seed.md
- [x] 3.2 Create a fresh test project directory
- [x] 3.3 Invoke seed agent on the test project and verify all files are generated correctly
- [ ] 3.4 Start a new session in the test project and verify TL bootstraps from the API
