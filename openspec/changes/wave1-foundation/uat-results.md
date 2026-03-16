# UAT Results: Wave 1 Foundation

**Tester:** Frank (QA)
**Date:** 2026-03-15
**Service URL:** https://teamforge-api-1019921786449.us-central1.run.app
**Environment:** Cloud Run (us-central1)

---

## Summary

- **Total tests executed:** 35
- **PASS:** 35
- **FAIL:** 0
- **Notes on data impact:** ORG-02 (update personal statement) modified the seeded personal statement during testing. It was restored to the original value after the test run. A UAT test dimension, a UAT test team, a UAT test agent, and a UAT project were created during testing. The dimension was deleted, the agent was deactivated, and the team and project remain in the system as inert test artifacts.

---

## Results

### Infrastructure and Health (INFRA)

| Test ID | Description | Result | Notes |
|---------|-------------|--------|-------|
| INFRA-01 | Health check returns healthy status | PASS | HTTP 200. Response: status=healthy, database=connected, timestamp in ISO 8601 with timezone. |
| INFRA-02 | Health check requires no authentication | PASS | Returns 200 with no API key. Also returns 200 with an invalid API key. Health endpoint never returns 401. |

### Authentication and API Key Security (AUTH)

| Test ID | Description | Result | Notes |
|---------|-------------|--------|-------|
| AUTH-01 | Valid API key grants access | PASS | HTTP 200 on GET /api/v1/orgs/hands-on-analytics with valid X-API-Key header. |
| AUTH-02 | Missing API key returns 401 | PASS | HTTP 401. Error body: code=MISSING_API_KEY, message="X-API-Key header is required." Proper JSON error format. |
| AUTH-03 | Invalid API key returns 401 | PASS | HTTP 401. Error body: code=INVALID_API_KEY, message="Invalid or revoked API key." Same error for both tf_ prefix and non-tf_ prefix keys -- no information leakage about key format. |
| AUTH-04 | Consistent error for non-tf-prefix key | PASS | Same INVALID_API_KEY response regardless of whether key has tf_ prefix. No format leakage. |
| AUTH-05 | API key resolves to correct org context | PASS | Valid key returns org data for Hands-On Analytics. All subsequent queries scoped to this org. |

### Organization CRUD (ORG)

| Test ID | Description | Result | Notes |
|---------|-------------|--------|-------|
| ORG-01 | Get org by slug | PASS | HTTP 200. Returns id, name, slug, personal_statement, evaluation_dimensions (8), suggested_norms (empty array), timestamps. All fields present. |
| ORG-02 | Update org personal statement | PASS | PATCH returns HTTP 200. GET confirms update. updated_at is later than created_at. Name and slug unchanged. |
| ORG-03 | Get evaluation dimensions | PASS | HTTP 200. Returns array of 8 dimensions with name, description, sort_order, and timestamps. All 8 sponsor dimensions present in correct order. |
| ORG-04 | Create evaluation dimension | PASS | HTTP 201. Dimension created with UUID, org_id, name, description, sort_order, and timestamps. (Cleaned up after test.) |
| ORG-05 | Get org by UUID | PASS | HTTP 200. Same response structure as slug-based lookup. UUID and slug both work as identifiers. |

### Team CRUD (TEAM)

| Test ID | Description | Result | Notes |
|---------|-------------|--------|-------|
| TEAM-01 | List teams | PASS | HTTP 200. Returns data array with pagination object (page=1, per_page=20, total, total_pages). Nautilus team present with status=active. |
| TEAM-02 | Get team nautilus | PASS | HTTP 200. Includes name, slug, status, roster (9 agents), norms (empty array), active_projects (empty array), timestamps. All expected keys present. |
| TEAM-03 | Create team | PASS | HTTP 201. Team created with UUID, org_id, status=active, empty roster, empty norms, empty active_projects, timestamps. |
| TEAM-04 | Team roster | PASS | Nautilus roster returns 9 agents. Each roster entry includes id, name, slug, role, agent_type, status. All 9 Nautilus team members accounted for. |
| TEAM-05 | Team slug and UUID lookup | PASS | Both GET /api/v1/teams/nautilus (slug) and GET /api/v1/teams/{uuid} return HTTP 200 with same data. |

### Agent CRUD (AGENT)

| Test ID | Description | Result | Notes |
|---------|-------------|--------|-------|
| AGENT-01 | List agents | PASS | HTTP 200. Returns 10 agents (9 Nautilus team members + 1 standalone specialist) with pagination. |
| AGENT-02 | Get agent (maya-ra) | PASS | HTTP 200. All identity fields present: name, slug, agent_type, role, persona, responsibilities, understanding, relationships, status, team_id, current_scores. current_scores includes all 8 dimensions with null scores and review_count=0. |
| AGENT-03 | Create agent | PASS | HTTP 201. Agent created with all provided fields. team_id=null, status=active, current_scores=[] (empty because no dimensions linked to unassigned agent). |
| AGENT-04 | Update agent | PASS | HTTP 200. Persona updated. Other fields unchanged. updated_at reflects change. |
| AGENT-05 | Deactivate agent | PASS | HTTP 200. Status changed to inactive. All identity fields preserved (persona, responsibilities, etc.). |
| AGENT-06 | Activate agent | PASS | HTTP 200. Status changed back to active. |
| AGENT-07 | Filter agents by team | PASS | GET /api/v1/agents?team_slug=nautilus returns exactly 9 agents, all belonging to Nautilus. |
| AGENT-08 | Filter agents by type | PASS | GET /api/v1/agents?agent_type=standalone_specialist returns 1 agent (Cloud Architect). Correct filtering by agent_type enum. |

### No-Delete Model Enforcement (NODELETE)

| Test ID | Description | Result | Notes |
|---------|-------------|--------|-------|
| NODELETE-01 | DELETE agent returns 405 | PASS | HTTP 405 Method Not Allowed. Agent not deleted. HTML response (not JSON), but status code is correct. |
| NODELETE-02 | DELETE team returns 405 | PASS | HTTP 405 Method Not Allowed. Team not deleted. Same HTML response pattern as NODELETE-01. |
| NODELETE-03 | Deactivation returns proper status | PASS | HTTP 200. Agent deactivated with status=inactive. Proper JSON response with all fields preserved. |

### Project References (PROJ)

| Test ID | Description | Result | Notes |
|---------|-------------|--------|-------|
| PROJ-01 | List projects | PASS | HTTP 200. Returns 2 seeded projects (Bookmark Manager, TeamForge/crucible) with pagination. |
| PROJ-02 | Create project | PASS | HTTP 201. Project created with UUID, org_id, slug, connected_teams (empty), timestamps. |
| PROJ-03 | Get project | PASS | HTTP 200. Returns project with all fields including connected_teams array. |

### Team Composition (COMP)

| Test ID | Description | Result | Notes |
|---------|-------------|--------|-------|
| COMP-01 | Add member to team | PASS | HTTP 200. Agent added to team roster. Response includes updated team with agent in roster array. |
| COMP-02 | Remove member from team | PASS | HTTP 200. Agent removed from roster. Agent still exists (status=active, team_id=null). Team roster empty after removal. |
| COMP-03 | Verify Nautilus roster intact | PASS | Nautilus team still has 9 agents after all composition tests on separate team. No data corruption from composition operations. |

### Seed Data Verification (SEED)

| Test ID | Description | Result | Notes |
|---------|-------------|--------|-------|
| SEED-01 | Verify seed data completeness | PASS | Nautilus team has 9 agents (Dante, Maya, Lena, Nadia, Chris, Sofia, Frank, Quinn, James). Org has 8 evaluation dimensions (Honesty & Transparency, Accountability, Communication, Growth Orientation, Constructive Challenge, Risk Management, Grace & Support, Craftsmanship). Personal statement is present and populated from sponsor's markdown file. |

---

## Observations

1. **405 responses return HTML, not JSON.** NODELETE-01 and NODELETE-02 return Flask's default HTML 405 page instead of the standardized JSON error format. This is cosmetically inconsistent with the rest of the API's error responses, though the status code is correct. Low severity -- worth addressing for API consistency but not blocking.

2. **current_scores on unassigned agents.** When an agent has no team_id, current_scores returns an empty array rather than the 8 dimension placeholders seen on team-assigned agents. This may be intentional (scores are only relevant to team members in context of the org's dimensions), but it could also be a gap -- standalone specialists should arguably still have org-level dimension scores. Worth a design clarification.

3. **Seeded projects exist.** Two project references (Bookmark Manager, TeamForge/crucible) were present in the seed data. The UAT cases did not explicitly list these as expected seed data, but they appear to be intentional.

4. **Standalone specialist in seed data.** A "Cloud Architect" standalone specialist agent was present in the seeded data. This is not listed in the Nautilus team roster (correct behavior for standalone_specialist type) but is returned in the full agent listing.

5. **Test data artifacts remain.** The UAT run created: uat-test-team (active team, empty roster), uat-agent (deactivated), and uat-project. These should be cleaned up or documented as expected test residue.

---

## Verdict

All 35 executed tests pass. The Wave 1 Foundation API meets the acceptance criteria defined in the UAT test cases for the tested categories. The API correctly implements health checks, API key authentication, org/team/agent/project CRUD, team composition management, the no-delete model, and seed data population.

The observations above are non-blocking items that should be tracked for follow-up.
