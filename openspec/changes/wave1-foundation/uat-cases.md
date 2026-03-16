# UAT Test Cases: Wave 1 Foundation

**Author:** Frank (QA)
**Date:** 2026-03-15
**Status:** Draft -- pending sponsor review before execution
**Specs under test:** org-team-agent-schema, core-crud-api, infrastructure-and-auth
**Design under test:** design.md (Wave 1 Foundation)

---

## How to Read This Document

Each test case has:
- **ID:** Category prefix + number (e.g., INFRA-01, AUTH-03)
- **Description:** What we are testing and why it matters
- **Preconditions:** What must be true before running the test
- **Steps:** Numbered actions to perform
- **Expected Result:** What the system must do for the test to pass

Categories are organized by domain. Happy path cases come first, followed by negative and edge cases within each category.

---

## Category 1: Infrastructure and Health (INFRA)

### INFRA-01: Health check returns healthy status

**Description:** The health endpoint confirms the service is running and connected to the database. This is the most basic smoke test -- if this fails, nothing else matters.

**Preconditions:** API service is deployed to Cloud Run. Cloud SQL instance is running.

**Steps:**
1. Send `GET /api/v1/health` with no headers (no API key).

**Expected Result:** HTTP 200. Response body contains `"status": "healthy"`, `"database": "connected"`, and a valid ISO 8601 timestamp.

---

### INFRA-02: Health check requires no authentication

**Description:** The health endpoint must be accessible without an API key. Monitoring systems and uptime checks do not carry credentials.

**Preconditions:** API service is deployed.

**Steps:**
1. Send `GET /api/v1/health` with no `X-API-Key` header.
2. Send `GET /api/v1/health` with an invalid `X-API-Key` header value.

**Expected Result:** Both requests return HTTP 200 with healthy status. The health endpoint never returns 401.

---

### INFRA-03: Service is accessible only via HTTPS

**Description:** Per infrastructure spec security requirements, there must be no HTTP fallback.

**Preconditions:** Cloud Run service URL is known.

**Steps:**
1. Attempt to reach the service via HTTP (non-TLS) URL.

**Expected Result:** The request is either rejected or automatically redirected to HTTPS. No plaintext HTTP responses are served.

---

### INFRA-04: Database has pgvector extension enabled

**Description:** The pgvector extension is a Wave 1 requirement for future embedding storage. The placeholder vector columns depend on it.

**Preconditions:** Database is provisioned. Schema migrations have been applied.

**Steps:**
1. Connect to the database directly (admin access).
2. Run `SELECT * FROM pg_extension WHERE extname = 'vector';`

**Expected Result:** The vector extension is listed. The experience_entries and review_entries tables contain vector(768) columns that accept data.

---

## Category 2: Authentication and API Key Security (AUTH)

### AUTH-01: Valid API key grants access

**Description:** A valid, active API key in the X-API-Key header grants access to API endpoints.

**Preconditions:** An org exists. An active API key has been generated for that org.

**Steps:**
1. Send `GET /api/v1/orgs/<org-slug>` with a valid `X-API-Key` header.

**Expected Result:** HTTP 200. Response contains the org data.

---

### AUTH-02: Missing API key returns 401

**Description:** All endpoints except health require authentication.

**Preconditions:** API service is deployed.

**Steps:**
1. Send `GET /api/v1/teams` with no `X-API-Key` header.

**Expected Result:** HTTP 401. Response body contains an error object with code and message. No data is returned.

---

### AUTH-03: Invalid API key returns 401

**Description:** A key that does not match any stored hash must be rejected.

**Preconditions:** API service is deployed.

**Steps:**
1. Send `GET /api/v1/teams` with `X-API-Key: tf_this_is_not_a_real_key_at_all`.

**Expected Result:** HTTP 401. The response does not reveal whether the key format was valid or whether the key simply was not found. A generic "unauthorized" message is acceptable.

---

### AUTH-04: Revoked API key returns 401

**Description:** An API key that has been deactivated (is_active = false) must no longer grant access.

**Preconditions:** An org exists. An API key has been generated and then revoked.

**Steps:**
1. Confirm the API key was previously valid (optional, if available from generation).
2. Revoke the key (set is_active = false).
3. Send `GET /api/v1/teams` with the revoked key.

**Expected Result:** HTTP 401.

---

### AUTH-05: API key is hashed in storage

**Description:** Raw API keys must never be stored in the database. This is a security requirement from the infrastructure spec.

**Preconditions:** An API key has been generated for an org.

**Steps:**
1. Connect to the database directly (admin access).
2. Query the `api_keys` table.
3. Examine the `key_hash` column values.

**Expected Result:** The stored value is a SHA-256 hash, not a plaintext key. The raw key value (starting with `tf_`) does not appear anywhere in the api_keys table. The `key_prefix` column contains only the first 8 characters of the original key.

---

### AUTH-06: API key resolves to correct org context

**Description:** A valid API key must scope all subsequent data access to the org associated with that key.

**Preconditions:** Two orgs exist (Org A and Org B). Each has its own API key. Org A has a team. Org B does not.

**Steps:**
1. Send `GET /api/v1/teams` with Org A's API key.
2. Send `GET /api/v1/teams` with Org B's API key.

**Expected Result:** Step 1 returns Org A's team(s). Step 2 returns an empty list. Neither request returns the other org's data.

---

### AUTH-07: Cross-org data access is impossible (org isolation)

**Description:** This is the most critical security test. An API key for Org A must never return data belonging to Org B, even if the caller knows the UUID or slug of Org B's resources.

**Preconditions:** Two orgs exist. Org A has an agent "maya-ra". Org B has a different agent. Each org has its own API key.

**Steps:**
1. Using Org B's API key, send `GET /api/v1/agents/maya-ra` (Org A's agent slug).
2. Using Org B's API key, send `GET /api/v1/agents/<org-a-agent-uuid>` (Org A's agent UUID).
3. Using Org B's API key, send `PATCH /api/v1/agents/maya-ra` with a body attempting to change the persona field.
4. Using Org B's API key, send `POST /api/v1/teams/<org-a-team-id>/members` with an agent_id from Org A.

**Expected Result:** All four requests return HTTP 403 or 404 (either is acceptable -- the system must not reveal whether the resource exists in another org). No data from Org A is returned or modified.

---

### AUTH-08: API key last_used_at is updated on use

**Description:** The api_keys table tracks when a key was last used.

**Preconditions:** An API key exists. Its `last_used_at` is either NULL or a known timestamp.

**Steps:**
1. Note the current `last_used_at` value for the key.
2. Send any valid authenticated request using that key.
3. Query the api_keys table for the updated `last_used_at`.

**Expected Result:** The `last_used_at` timestamp has been updated to approximately the current time.

---

## Category 3: Organization CRUD (ORG)

### ORG-01: Create an org with all fields

**Description:** Create an organization with name, slug, and personal statement.

**Preconditions:** A valid API key exists (or this is the bootstrap case where the key is generated alongside the org).

**Steps:**
1. Send `POST /api/v1/orgs` with body:
   ```json
   {
     "name": "Hands-On Analytics",
     "slug": "hands-on-analytics",
     "personal_statement": "Be honest. If you don't know, say you don't know..."
   }
   ```

**Expected Result:** HTTP 201. Response includes the org with a system-generated UUID, the provided name, slug, personal statement, and ISO 8601 timestamps for created_at and updated_at.

---

### ORG-02: Get an org by slug

**Description:** Retrieve org data using the URL-safe slug identifier.

**Preconditions:** Org "hands-on-analytics" exists.

**Steps:**
1. Send `GET /api/v1/orgs/hands-on-analytics`.

**Expected Result:** HTTP 200. Response includes org fields, evaluation_dimensions array (may be empty), and suggested_norms array (may be empty).

---

### ORG-03: Get an org by UUID

**Description:** Retrieve org data using the system-generated UUID.

**Preconditions:** Org exists with a known UUID.

**Steps:**
1. Send `GET /api/v1/orgs/<uuid>`.

**Expected Result:** HTTP 200. Same response structure as ORG-02.

---

### ORG-04: Update org personal statement

**Description:** The sponsor's personal statement is a living document that can be updated.

**Preconditions:** Org exists with an initial personal statement.

**Steps:**
1. Send `PATCH /api/v1/orgs/hands-on-analytics` with body:
   ```json
   {
     "personal_statement": "Updated personal statement with new values."
   }
   ```
2. Send `GET /api/v1/orgs/hands-on-analytics`.

**Expected Result:** PATCH returns HTTP 200. GET confirms the personal_statement has been updated. The updated_at timestamp is later than created_at. The name and slug remain unchanged.

---

### ORG-05: Slug is immutable after creation

**Description:** Per spec, org slug cannot be changed after creation.

**Preconditions:** Org "hands-on-analytics" exists.

**Steps:**
1. Send `PATCH /api/v1/orgs/hands-on-analytics` with body:
   ```json
   {
     "slug": "new-slug"
   }
   ```

**Expected Result:** HTTP 400 or 422. The slug field is rejected as not updatable. The slug remains "hands-on-analytics".

---

### ORG-06: Duplicate org slug returns 409

**Description:** Slugs are unique. Attempting to create a second org with the same slug must fail.

**Preconditions:** Org with slug "hands-on-analytics" exists.

**Steps:**
1. Send `POST /api/v1/orgs` with body containing `"slug": "hands-on-analytics"`.

**Expected Result:** HTTP 409 (Conflict). Error message indicates the slug is already in use.

---

### ORG-07: Create org with null personal statement

**Description:** Personal statement is nullable. An org can be created without one.

**Preconditions:** None specific.

**Steps:**
1. Send `POST /api/v1/orgs` with body:
   ```json
   {
     "name": "Empty Org",
     "slug": "empty-org"
   }
   ```

**Expected Result:** HTTP 201. The org is created with personal_statement as null.

---

### ORG-08: Create org with missing required fields

**Description:** Name and slug are required. Missing them must be rejected.

**Preconditions:** None specific.

**Steps:**
1. Send `POST /api/v1/orgs` with body `{"name": "No Slug Org"}` (missing slug).
2. Send `POST /api/v1/orgs` with body `{"slug": "no-name-org"}` (missing name).
3. Send `POST /api/v1/orgs` with empty body `{}`.

**Expected Result:** All three return HTTP 400 or 422 with a clear validation error identifying the missing field(s).

---

### ORG-09: Get nonexistent org returns 404

**Description:** Requesting an org that does not exist must return 404.

**Preconditions:** No org with slug "does-not-exist" exists.

**Steps:**
1. Send `GET /api/v1/orgs/does-not-exist`.

**Expected Result:** HTTP 404. Error message indicates the org was not found.

---

## Category 4: Evaluation Dimensions (DIM)

### DIM-01: Create evaluation dimensions for an org

**Description:** The sponsor defines the eight evaluation dimensions at the org level.

**Preconditions:** Org exists.

**Steps:**
1. Send `POST /api/v1/orgs/hands-on-analytics/dimensions` with body:
   ```json
   {
     "name": "Honesty & Transparency",
     "description": "Presents uncertainty honestly, shows reasoning, surfaces problems early",
     "sort_order": 1
   }
   ```
2. Repeat for all eight dimensions (or a representative subset for UAT).

**Expected Result:** HTTP 201 for each. Each dimension has a UUID, is linked to the org, and retains the provided name, description, and sort_order.

---

### DIM-02: List dimensions for an org

**Description:** All dimensions for an org are returned in a single non-paginated list.

**Preconditions:** Multiple dimensions have been created for the org.

**Steps:**
1. Send `GET /api/v1/orgs/hands-on-analytics/dimensions`.

**Expected Result:** HTTP 200. Response is an array of all dimensions. Each includes id, name, description, sort_order, and timestamps.

---

### DIM-03: Update a dimension name

**Description:** Dimensions can be renamed (e.g., if the sponsor refines the framework).

**Preconditions:** A dimension "Honesty & Transparency" exists.

**Steps:**
1. Send `PATCH /api/v1/orgs/hands-on-analytics/dimensions/<dim-id>` with body:
   ```json
   {
     "name": "Honesty, Transparency & Candor"
   }
   ```
2. Retrieve the dimension to confirm.

**Expected Result:** The dimension name is updated. updated_at reflects the change.

---

### DIM-04: Delete a dimension with no score references

**Description:** Dimensions without any scores referencing them can be deleted.

**Preconditions:** A dimension exists. No agent_scores rows reference it.

**Steps:**
1. Send `DELETE /api/v1/orgs/hands-on-analytics/dimensions/<dim-id>`.

**Expected Result:** HTTP 200 or 204. The dimension is removed. Subsequent GET does not include it.

---

### DIM-05: Cannot delete a dimension with existing scores

**Description:** Dimensions that have been used for scoring are protected from deletion to preserve historical data.

**Preconditions:** A dimension exists. At least one agent_scores row references it.

**Steps:**
1. Send `DELETE /api/v1/orgs/hands-on-analytics/dimensions/<dim-id>`.

**Expected Result:** HTTP 409 (Conflict). Error message explains the dimension cannot be deleted because scores reference it. The dimension is suggested to be renamed instead.

---

### DIM-06: Duplicate dimension name within an org returns 409

**Description:** Each dimension name must be unique within its org.

**Preconditions:** Dimension "Honesty & Transparency" exists in the org.

**Steps:**
1. Send `POST /api/v1/orgs/hands-on-analytics/dimensions` with body containing `"name": "Honesty & Transparency"`.

**Expected Result:** HTTP 409. Error indicates duplicate dimension name.

---

### DIM-07: Dimensions are included in org GET response

**Description:** When retrieving an org, the evaluation dimensions should be included in the response.

**Preconditions:** Org has multiple dimensions defined.

**Steps:**
1. Send `GET /api/v1/orgs/hands-on-analytics`.

**Expected Result:** Response includes an `evaluation_dimensions` array with all the org's dimensions.

---

## Category 5: Team CRUD (TEAM)

### TEAM-01: Create a team within an org

**Description:** Create a named team with slug and description.

**Preconditions:** Org exists.

**Steps:**
1. Send `POST /api/v1/teams` with body:
   ```json
   {
     "name": "Nautilus",
     "slug": "nautilus",
     "description": "Primary development team"
   }
   ```

**Expected Result:** HTTP 201. Response includes team with UUID, org_id matching the API key's org, status "active", and timestamps.

---

### TEAM-02: Get a team includes roster, norms, and project connections

**Description:** The team GET response is a comprehensive view of the team's state.

**Preconditions:** Team "nautilus" exists with at least one member, one norm, and one active project connection.

**Steps:**
1. Send `GET /api/v1/teams/nautilus`.

**Expected Result:** HTTP 200. Response includes:
- Team fields (id, name, slug, description, status, timestamps)
- Roster: array of agent summaries for agents currently on the team
- Norms: array of team norms
- Active project connections: array of connected projects

---

### TEAM-03: List teams in an org (paginated)

**Description:** List endpoint returns paginated results.

**Preconditions:** Multiple teams exist in the org (create at least 2).

**Steps:**
1. Send `GET /api/v1/teams`.
2. Send `GET /api/v1/teams?page=1&per_page=1`.

**Expected Result:** Step 1 returns all teams with pagination metadata (total, page, per_page, total_pages). Step 2 returns exactly 1 team with pagination showing total > 1.

---

### TEAM-04: Update team name and description

**Description:** Team name and description are mutable.

**Preconditions:** Team "nautilus" exists.

**Steps:**
1. Send `PATCH /api/v1/teams/nautilus` with body:
   ```json
   {
     "name": "Nautilus Prime",
     "description": "Updated team description"
   }
   ```
2. Retrieve the team.

**Expected Result:** Name and description are updated. Slug remains "nautilus". updated_at reflects the change.

---

### TEAM-05: Team slug is immutable

**Description:** Team slug cannot be changed after creation.

**Preconditions:** Team exists.

**Steps:**
1. Send `PATCH /api/v1/teams/nautilus` with body `{"slug": "new-slug"}`.

**Expected Result:** HTTP 400 or 422. Slug remains unchanged.

---

### TEAM-06: Duplicate team slug within org returns 409

**Description:** Team slugs must be unique within an org.

**Preconditions:** Team with slug "nautilus" exists.

**Steps:**
1. Send `POST /api/v1/teams` with body containing `"slug": "nautilus"`.

**Expected Result:** HTTP 409.

---

### TEAM-07: Deactivate a team with no active members

**Description:** A team with no active members can be deactivated.

**Preconditions:** Team exists with no agents assigned (or all agents have been removed).

**Steps:**
1. Send `PATCH /api/v1/teams/nautilus/deactivate`.
2. Send `GET /api/v1/teams/nautilus`.

**Expected Result:** Step 1 returns HTTP 200. Step 2 shows status = "inactive". The team's norms, description, and other data are preserved.

---

### TEAM-08: Cannot deactivate a team with active members

**Description:** Teams with assigned agents cannot be deactivated. Agents must be reassigned or unassigned first.

**Preconditions:** Team has at least one agent assigned to it.

**Steps:**
1. Send `PATCH /api/v1/teams/nautilus/deactivate`.

**Expected Result:** HTTP 409. Error message indicates the team still has active members and they must be removed first.

---

### TEAM-09: Deactivated teams excluded from default list

**Description:** Inactive teams do not appear in default team listings.

**Preconditions:** Team "nautilus" has been deactivated (status = inactive). Another active team exists.

**Steps:**
1. Send `GET /api/v1/teams`.
2. Send `GET /api/v1/teams?include_inactive=true`.

**Expected Result:** Step 1 does not include the inactive team. Step 2 includes both active and inactive teams.

---

### TEAM-10: Reactivate a deactivated team

**Description:** A deactivated team can be brought back to active status.

**Preconditions:** Team is currently inactive.

**Steps:**
1. Send `PATCH /api/v1/teams/nautilus/activate`.
2. Send `GET /api/v1/teams`.

**Expected Result:** Step 1 returns HTTP 200. Step 2 includes the team with status = "active".

---

### TEAM-11: Teams are never deleted

**Description:** There is no DELETE endpoint for teams. This is a sponsor directive.

**Preconditions:** Team exists.

**Steps:**
1. Send `DELETE /api/v1/teams/nautilus`.

**Expected Result:** HTTP 405 (Method Not Allowed) or 404 (no such route). The team is not removed from the database.

---

### TEAM-12: Get nonexistent team returns 404

**Description:** Requesting a team that does not exist returns 404.

**Preconditions:** No team with slug "ghost-team" exists.

**Steps:**
1. Send `GET /api/v1/teams/ghost-team`.

**Expected Result:** HTTP 404.

---

## Category 6: Agent CRUD (AGENT)

### AGENT-01: Create an agent with team assignment

**Description:** Create a team_member agent assigned to an existing team.

**Preconditions:** Org and team "nautilus" exist.

**Steps:**
1. Send `POST /api/v1/agents` with body:
   ```json
   {
     "name": "Maya",
     "slug": "maya-ra",
     "agent_type": "team_member",
     "role": "Requirements Architect",
     "persona": "Maya is direct and methodical...",
     "responsibilities": "Remove dangerous ambiguity...",
     "understanding": null,
     "relationships": null,
     "team_id": "<nautilus-team-uuid>"
   }
   ```

**Expected Result:** HTTP 201. Agent is created with all fields. team_id matches the provided value. Status is "active".

---

### AGENT-02: Create an agent without team assignment (hired for growth)

**Description:** A team_member agent can be created without a team. They are "hired for growth" and assigned later.

**Preconditions:** Org exists.

**Steps:**
1. Send `POST /api/v1/agents` with body containing `"agent_type": "team_member"` and no `team_id` field (or `"team_id": null`).

**Expected Result:** HTTP 201. Agent is created with team_id = null. Status is "active".

---

### AGENT-03: Create a standalone specialist

**Description:** Standalone specialists belong to the org directly, never to a team.

**Preconditions:** Org exists.

**Steps:**
1. Send `POST /api/v1/agents` with body:
   ```json
   {
     "name": "Cloud Architect",
     "slug": "cloud-architect",
     "agent_type": "standalone_specialist",
     "role": "Cloud Infrastructure Specialist",
     "persona": "Focused and precise...",
     "responsibilities": "GCP infrastructure decisions..."
   }
   ```

**Expected Result:** HTTP 201. Agent is created with agent_type = "standalone_specialist" and team_id = null.

---

### AGENT-04: Get agent includes identity fields and current scores

**Description:** The agent GET response includes all identity fields and the current_scores array.

**Preconditions:** Agent "maya-ra" exists. Evaluation dimensions exist. Some dimensions have scores, some do not.

**Steps:**
1. Send `GET /api/v1/agents/maya-ra`.

**Expected Result:** HTTP 200. Response includes:
- All identity fields: name, slug, agent_type, role, persona, responsibilities, understanding, relationships
- Status and timestamps
- team membership info (team_id, or team object)
- current_scores array with one entry per evaluation dimension
- Dimensions with no reviews show current_score = null, rolling_average = null, review_count = 0, last_reviewed_at = null

---

### AGENT-05: Get agent by UUID

**Description:** Agents can be retrieved by UUID in addition to slug.

**Preconditions:** Agent exists with a known UUID.

**Steps:**
1. Send `GET /api/v1/agents/<uuid>`.

**Expected Result:** HTTP 200. Same response as slug-based lookup.

---

### AGENT-06: Update agent identity fields

**Description:** Persona, responsibilities, understanding, relationships, role, and name are updatable.

**Preconditions:** Agent "maya-ra" exists.

**Steps:**
1. Send `PATCH /api/v1/agents/maya-ra` with body:
   ```json
   {
     "persona": "Maya has evolved. She is now more collaborative...",
     "understanding": "I understand my role as the spec gatekeeper."
   }
   ```
2. Retrieve the agent.

**Expected Result:** Updated fields reflect the new values. Other fields remain unchanged. updated_at is newer.

---

### AGENT-07: Agent slug is immutable

**Description:** Agent slug cannot be changed after creation.

**Preconditions:** Agent "maya-ra" exists.

**Steps:**
1. Send `PATCH /api/v1/agents/maya-ra` with body `{"slug": "maya-new"}`.

**Expected Result:** HTTP 400 or 422. Slug remains "maya-ra".

---

### AGENT-08: Agent type is immutable

**Description:** Agent type (team_member vs standalone_specialist) cannot be changed after creation.

**Preconditions:** Agent with agent_type "team_member" exists.

**Steps:**
1. Send `PATCH /api/v1/agents/maya-ra` with body `{"agent_type": "standalone_specialist"}`.

**Expected Result:** HTTP 400 or 422. Agent type remains "team_member".

---

### AGENT-09: Team ID is not updatable through PATCH

**Description:** Team assignment is managed through the team composition endpoints, not the agent PATCH endpoint.

**Preconditions:** Agent exists.

**Steps:**
1. Send `PATCH /api/v1/agents/maya-ra` with body `{"team_id": "<some-team-uuid>"}`.

**Expected Result:** HTTP 400 or 422. The team_id field is rejected in the PATCH body. Agent's team assignment is unchanged.

---

### AGENT-10: Duplicate agent slug within org returns 409

**Description:** Agent slugs must be unique within an org.

**Preconditions:** Agent with slug "maya-ra" exists in the org.

**Steps:**
1. Send `POST /api/v1/agents` with body containing `"slug": "maya-ra"`.

**Expected Result:** HTTP 409.

---

### AGENT-11: List agents with team filter

**Description:** The list endpoint supports filtering by team.

**Preconditions:** Multiple agents exist, some on team "nautilus", some unassigned.

**Steps:**
1. Send `GET /api/v1/agents?team_slug=nautilus`.

**Expected Result:** HTTP 200. Only agents assigned to team "nautilus" are returned.

---

### AGENT-12: List agents filtered by unassigned

**Description:** List only agents with no team assignment.

**Preconditions:** At least one agent has team_id = null.

**Steps:**
1. Send `GET /api/v1/agents?unassigned=true`.

**Expected Result:** HTTP 200. Only agents with no team assignment are returned (both unassigned team_members and standalone specialists).

---

### AGENT-13: List agents filtered by agent type

**Description:** List only standalone specialists (or only team members).

**Preconditions:** At least one standalone specialist and one team member exist.

**Steps:**
1. Send `GET /api/v1/agents?agent_type=standalone_specialist`.
2. Send `GET /api/v1/agents?agent_type=team_member`.

**Expected Result:** Step 1 returns only standalone specialists. Step 2 returns only team members.

---

### AGENT-14: Deactivate an agent

**Description:** Agents are deactivated, never deleted.

**Preconditions:** Agent "maya-ra" exists and is active.

**Steps:**
1. Send `PATCH /api/v1/agents/maya-ra/deactivate`.
2. Send `GET /api/v1/agents/maya-ra`.

**Expected Result:** Step 1 returns HTTP 200. Step 2 shows status = "inactive". All identity fields, persona, responsibilities, etc. are preserved.

---

### AGENT-15: Deactivated agents excluded from default list

**Description:** Inactive agents do not appear in default listings.

**Preconditions:** Agent "maya-ra" is inactive. Other active agents exist.

**Steps:**
1. Send `GET /api/v1/agents`.
2. Send `GET /api/v1/agents?include_inactive=true`.

**Expected Result:** Step 1 does not include the inactive agent. Step 2 includes both active and inactive agents.

---

### AGENT-16: Reactivate a deactivated agent

**Description:** Inactive agents can be reactivated.

**Preconditions:** Agent is currently inactive.

**Steps:**
1. Send `PATCH /api/v1/agents/maya-ra/activate`.
2. Send `GET /api/v1/agents`.

**Expected Result:** Agent's status is "active". They appear in the default agent listing.

---

### AGENT-17: Agents are never deleted

**Description:** There is no DELETE endpoint for agents. Sponsor directive.

**Preconditions:** Agent exists.

**Steps:**
1. Send `DELETE /api/v1/agents/maya-ra`.

**Expected Result:** HTTP 405 (Method Not Allowed) or 404 (no such route). The agent and all their data remain in the database.

---

### AGENT-18: Create agent with missing required fields

**Description:** Name, slug, agent_type, role, persona, and responsibilities are all NOT NULL.

**Preconditions:** Org exists.

**Steps:**
1. Send `POST /api/v1/agents` with body missing `persona` field.
2. Send `POST /api/v1/agents` with body missing `role` field.
3. Send `POST /api/v1/agents` with body missing `name` field.
4. Send `POST /api/v1/agents` with empty body `{}`.

**Expected Result:** All return HTTP 400 or 422 with clear validation errors identifying the missing required field(s).

---

### AGENT-19: Create agent with empty string required fields

**Description:** Required text fields should not accept empty strings as valid values.

**Preconditions:** Org exists.

**Steps:**
1. Send `POST /api/v1/agents` with body containing `"persona": ""` (empty string) and all other fields valid.
2. Send `POST /api/v1/agents` with body containing `"name": ""`.

**Expected Result:** HTTP 400 or 422. Empty strings are not valid for NOT NULL text fields that define agent identity.

---

### AGENT-20: Get nonexistent agent returns 404

**Description:** Requesting an agent that does not exist returns 404.

**Preconditions:** No agent with slug "nobody" exists in this org.

**Steps:**
1. Send `GET /api/v1/agents/nobody`.

**Expected Result:** HTTP 404.

---

### AGENT-21: Agent list pagination

**Description:** Agent list endpoint supports pagination.

**Preconditions:** More than 1 agent exists in the org.

**Steps:**
1. Send `GET /api/v1/agents?page=1&per_page=2`.
2. Send `GET /api/v1/agents?page=2&per_page=2`.

**Expected Result:** Each response includes a `pagination` object with total, page, per_page, total_pages. Different pages return different agents. Total count is consistent across pages.

---

### AGENT-22: Create agent with invalid agent_type

**Description:** Agent type must be one of the allowed values.

**Preconditions:** Org exists.

**Steps:**
1. Send `POST /api/v1/agents` with body containing `"agent_type": "robot"`.

**Expected Result:** HTTP 400 or 422. Error indicates invalid agent_type value.

---

## Category 7: Team Composition (COMP)

### COMP-01: Add an agent to a team

**Description:** Assign an unassigned team_member agent to a team.

**Preconditions:** Team "nautilus" exists. Agent "maya-ra" exists with agent_type = "team_member" and team_id = null.

**Steps:**
1. Send `POST /api/v1/teams/nautilus/members` with body:
   ```json
   {
     "agent_id": "<maya-ra-uuid>"
   }
   ```
2. Send `GET /api/v1/teams/nautilus`.

**Expected Result:** Step 1 returns HTTP 200 with updated roster. Step 2 confirms Maya appears in the team roster.

---

### COMP-02: Remove an agent from a team

**Description:** Removing an agent from a team sets their team_id to null. They are not deleted.

**Preconditions:** Agent "maya-ra" is assigned to team "nautilus".

**Steps:**
1. Send `DELETE /api/v1/teams/nautilus/members/maya-ra`.
2. Send `GET /api/v1/agents/maya-ra`.
3. Send `GET /api/v1/teams/nautilus`.

**Expected Result:** Step 1 returns HTTP 200. Step 2 shows agent with team_id = null (agent still exists, still active). Step 3 shows team roster without Maya.

---

### COMP-03: Cannot add standalone specialist to a team

**Description:** Standalone specialists exist at the org level and cannot be added to teams.

**Preconditions:** Team exists. Agent with agent_type = "standalone_specialist" exists.

**Steps:**
1. Send `POST /api/v1/teams/nautilus/members` with body containing the standalone specialist's agent_id.

**Expected Result:** HTTP 422. Error indicates standalone specialists cannot be added to teams.

---

### COMP-04: Cannot add agent already on another team

**Description:** An agent can belong to at most one team at a time.

**Preconditions:** Two teams exist: "nautilus" and "other-team". Agent "maya-ra" is on "nautilus".

**Steps:**
1. Send `POST /api/v1/teams/other-team/members` with body containing maya-ra's agent_id.

**Expected Result:** HTTP 409 or 422. Error indicates the agent is already assigned to another team. To reassign, remove from the current team first.

---

### COMP-05: Cannot add agent from a different org

**Description:** Cross-org team composition must be impossible.

**Preconditions:** Two orgs exist with separate API keys. Org A has a team. Org B has an agent.

**Steps:**
1. Using Org A's API key, send `POST /api/v1/teams/<org-a-team>/members` with body containing Org B's agent UUID.

**Expected Result:** HTTP 403, 404, or 422. The operation fails. The agent from Org B is not added to Org A's team.

---

### COMP-06: Add agent to team, then remove, then re-add

**Description:** The full lifecycle of team membership changes works correctly.

**Preconditions:** Team and agent exist. Agent is unassigned.

**Steps:**
1. Add agent to team via `POST /api/v1/teams/nautilus/members`.
2. Confirm agent is on team via `GET /api/v1/teams/nautilus`.
3. Remove agent via `DELETE /api/v1/teams/nautilus/members/<agent>`.
4. Confirm agent is no longer on team.
5. Re-add agent via `POST /api/v1/teams/nautilus/members`.
6. Confirm agent is back on team.

**Expected Result:** All steps succeed. The agent can be freely added and removed without data corruption.

---

### COMP-07: Cannot add agent to a deactivated team

**Description:** If a team is inactive, adding members to it should not be allowed (or the behavior should be explicitly defined).

**Preconditions:** Team is deactivated (status = inactive). An unassigned agent exists.

**Steps:**
1. Send `POST /api/v1/teams/<inactive-team>/members` with the agent's ID.

**Expected Result:** HTTP 409 or 422. Cannot add members to an inactive team.

---

## Category 8: Project References and Team-Project Connections (PROJ)

### PROJ-01: Create a project reference

**Description:** Create a lightweight project reference entity.

**Preconditions:** Org exists.

**Steps:**
1. Send `POST /api/v1/projects` with body:
   ```json
   {
     "name": "TeamForge",
     "slug": "crucible",
     "description": "Persistent agent team service"
   }
   ```

**Expected Result:** HTTP 201. Project reference is created with org_id, UUID, and timestamps.

---

### PROJ-02: Get project reference includes connected teams

**Description:** The project GET response shows which teams are currently connected.

**Preconditions:** Project "crucible" exists. At least one team is connected to it.

**Steps:**
1. Send `GET /api/v1/projects/crucible`.

**Expected Result:** HTTP 200. Response includes project fields and a connected_teams array listing teams with active connections.

---

### PROJ-03: List project references (paginated)

**Description:** List endpoint returns paginated project references.

**Preconditions:** Multiple project references exist.

**Steps:**
1. Send `GET /api/v1/projects`.

**Expected Result:** HTTP 200. Paginated list of project references.

---

### PROJ-04: Update project reference

**Description:** Name and description are updatable. Slug is immutable.

**Preconditions:** Project "crucible" exists.

**Steps:**
1. Send `PATCH /api/v1/projects/crucible` with body `{"description": "Updated description"}`.
2. Send `PATCH /api/v1/projects/crucible` with body `{"slug": "new-slug"}`.

**Expected Result:** Step 1 succeeds (HTTP 200). Step 2 is rejected (HTTP 400 or 422).

---

### PROJ-05: Delete project reference with no active connections

**Description:** Project references can be deleted when no teams are connected.

**Preconditions:** Project exists with no active team connections.

**Steps:**
1. Send `DELETE /api/v1/projects/<project-slug>`.

**Expected Result:** HTTP 200 or 204. Project is removed.

---

### PROJ-06: Cannot delete project reference with active team connections

**Description:** Projects with active connections must have teams disconnected first.

**Preconditions:** Project exists with at least one active team connection.

**Steps:**
1. Send `DELETE /api/v1/projects/crucible`.

**Expected Result:** HTTP 409. Error indicates teams must be disconnected first.

---

### PROJ-07: Duplicate project slug returns 409

**Description:** Project slugs must be unique within an org.

**Preconditions:** Project with slug "crucible" exists.

**Steps:**
1. Send `POST /api/v1/projects` with body containing `"slug": "crucible"`.

**Expected Result:** HTTP 409.

---

### PROJ-08: Connect a team to a project

**Description:** A team can be connected to a project reference.

**Preconditions:** Team "nautilus" and project "crucible" exist.

**Steps:**
1. Send `POST /api/v1/teams/nautilus/projects` with body:
   ```json
   {
     "project_id": "<crucible-uuid>"
   }
   ```

**Expected Result:** HTTP 201. Connection record created with connected_at timestamp and disconnected_at = null.

---

### PROJ-09: Disconnect a team from a project preserves history

**Description:** Disconnecting sets disconnected_at rather than deleting the connection record.

**Preconditions:** Team "nautilus" is connected to project "crucible".

**Steps:**
1. Send `DELETE /api/v1/teams/nautilus/projects/crucible`.
2. Verify in the database (or via API) that the connection record still exists with a disconnected_at timestamp.

**Expected Result:** The connection record is preserved. disconnected_at is set to approximately the current time. The team no longer shows as actively connected to the project.

---

### PROJ-10: Duplicate active connection returns 409

**Description:** A team cannot have two active connections to the same project simultaneously.

**Preconditions:** Team "nautilus" is already connected to project "crucible" (disconnected_at = null).

**Steps:**
1. Send `POST /api/v1/teams/nautilus/projects` with the same project_id.

**Expected Result:** HTTP 409. Error indicates an active connection already exists.

---

### PROJ-11: Reconnect team to project after disconnect

**Description:** A team can be disconnected from a project and then reconnected, creating a new connection record.

**Preconditions:** Team was connected to project, then disconnected.

**Steps:**
1. Confirm the team is disconnected from the project.
2. Send `POST /api/v1/teams/nautilus/projects` with the project_id.
3. Verify the connection.

**Expected Result:** HTTP 201. A new connection record is created. The old record (with disconnected_at) is preserved. Both records exist in the connection history.

---

### PROJ-12: Team can be connected to multiple projects simultaneously

**Description:** A team is not limited to one project at a time.

**Preconditions:** Team exists. Two project references exist.

**Steps:**
1. Connect team to project A.
2. Connect team to project B.
3. Get the team.

**Expected Result:** Both projects appear in the team's active project connections.

---

## Category 9: Team Norms (NORM)

### NORM-01: Create a team norm

**Description:** Norms are living operating agreements for a team.

**Preconditions:** Team "nautilus" exists.

**Steps:**
1. Send a request to create a norm for team "nautilus" with title "No spec, no work" and body describing the norm, with status "active".

**Expected Result:** Norm is created with the provided fields and timestamps. The norm is linked to the team.

---

### NORM-02: Team norms appear in team GET response

**Description:** When retrieving a team, its norms are included.

**Preconditions:** Team has at least one norm.

**Steps:**
1. Send `GET /api/v1/teams/nautilus`.

**Expected Result:** Response includes a norms array with the team's norms, each showing title, body, status, and promoted_to_org flag.

---

### NORM-03: Create norm with different statuses

**Description:** Norms can be created in 'active', 'proposed', 'rejected', or 'retired' status. Wave 1 allows direct creation; the workflow is Wave 2.

**Preconditions:** Team exists.

**Steps:**
1. Create a norm with status "active".
2. Create a norm with status "proposed".

**Expected Result:** Both norms are created with their respective statuses.

---

## Category 10: Org Suggested Norms (ONORM)

### ONORM-01: Create an org-level suggested norm

**Description:** Norms can be promoted from teams to org-level suggestions for new teams.

**Preconditions:** Org exists. Optionally, a source team exists.

**Steps:**
1. Create an org suggested norm with title, body, and source_team_id.
2. Send `GET /api/v1/orgs/hands-on-analytics`.

**Expected Result:** The suggested norm appears in the org's suggested_norms array in the GET response.

---

### ONORM-02: Org suggested norm with no source team

**Description:** Suggested norms can exist without a source team (e.g., sponsor-created norms).

**Preconditions:** Org exists.

**Steps:**
1. Create an org suggested norm with source_team_id = null.

**Expected Result:** Norm is created successfully with null source_team_id.

---

## Category 11: Data Integrity and Referential Constraints (INTEG)

### INTEG-01: Cannot create a team in a nonexistent org

**Description:** Foreign key constraints enforce referential integrity.

**Preconditions:** API service is running. The API key resolves to a valid org.

**Steps:**
1. Attempt to directly insert a team row (via database) with an org_id that does not exist.

**Expected Result:** The database rejects the insert with a foreign key violation.

---

### INTEG-02: Cannot create an agent referencing a nonexistent team

**Description:** If team_id is provided, it must reference a valid team.

**Preconditions:** Org exists. No team with the given UUID exists.

**Steps:**
1. Send `POST /api/v1/agents` with a team_id UUID that does not correspond to any team.

**Expected Result:** HTTP 404 or 422. Error indicates the referenced team does not exist.

---

### INTEG-03: Agent referencing a team in a different org is rejected

**Description:** An agent's team must be within the same org.

**Preconditions:** Two orgs exist. Org A has a team. Org B is the API key's org.

**Steps:**
1. Using Org B's API key, send `POST /api/v1/agents` with team_id referencing Org A's team.

**Expected Result:** HTTP 403, 404, or 422. The agent is not created with a cross-org team reference.

---

### INTEG-04: Unique constraint on agent_scores (agent_id, dimension_id)

**Description:** Each agent can have at most one score per evaluation dimension.

**Preconditions:** An agent_scores record exists for agent X on dimension Y.

**Steps:**
1. Attempt to insert a second agent_scores row for the same agent_id and dimension_id (via database or seed script).

**Expected Result:** The database rejects the duplicate with a unique constraint violation.

---

### INTEG-05: Deactivated agent retains all data

**Description:** Deactivation must not cascade to delete or null out any related data.

**Preconditions:** Agent has identity fields, team membership, and score records.

**Steps:**
1. Deactivate the agent.
2. Query the database directly for the agent's row, agent_scores rows, and any other related records.

**Expected Result:** All data is intact. Identity fields, scores, team_id (if applicable), and all timestamps are preserved. Only the status field changed to "inactive".

---

### INTEG-06: Deactivated team retains all data

**Description:** Team deactivation preserves norms, project connection history, and metadata.

**Preconditions:** Team has norms, project connections (active and historical), and metadata.

**Steps:**
1. Remove all agents from the team (required before deactivation).
2. Deactivate the team.
3. Query the team, its norms, and its project connection history.

**Expected Result:** All norms remain. All project connection records (both active and historical) remain. Team metadata is preserved. Only status changed.

---

### INTEG-07: org_id present on all top-level entities

**Description:** Every top-level entity must have org_id. This is the foundation of multi-tenant isolation.

**Preconditions:** Schema has been applied.

**Steps:**
1. Inspect the schema for all tables: organizations, teams, agents, project_references, evaluation_dimensions, experience_entries, review_entries, org_suggested_norms.

**Expected Result:** Every table either has an org_id column directly or reaches an org through a foreign key chain (e.g., team_norms -> teams -> organizations). No table is orphaned from the org hierarchy.

---

### INTEG-08: Timestamps are consistently ISO 8601 with timezone

**Description:** All API responses must use ISO 8601 timestamps with timezone.

**Preconditions:** Various entities have been created and updated.

**Steps:**
1. Create an org, team, agent, and project.
2. Update each entity.
3. Inspect all timestamp fields in all responses.

**Expected Result:** Every created_at and updated_at field is in ISO 8601 format with timezone (e.g., `2026-03-15T14:30:00Z`). No timestamps are missing timezone indicators.

---

## Category 12: Pagination (PAGE)

### PAGE-01: Default pagination values

**Description:** List endpoints default to page=1, per_page=20.

**Preconditions:** At least 1 entity exists for the list being tested.

**Steps:**
1. Send `GET /api/v1/agents` with no pagination parameters.

**Expected Result:** Response includes pagination object with page=1, per_page=20, total (correct count), and total_pages (calculated correctly).

---

### PAGE-02: Custom per_page value

**Description:** Callers can control page size.

**Preconditions:** At least 3 agents exist.

**Steps:**
1. Send `GET /api/v1/agents?per_page=2`.

**Expected Result:** At most 2 agents returned. Pagination shows per_page=2 and total_pages correctly calculated.

---

### PAGE-03: per_page maximum is 100

**Description:** The per_page parameter has an upper limit.

**Preconditions:** Any entities exist.

**Steps:**
1. Send `GET /api/v1/agents?per_page=200`.

**Expected Result:** Either HTTP 400 (rejected) or the system caps at 100 and returns at most 100 results.

---

### PAGE-04: Page beyond total pages returns empty data

**Description:** Requesting a page beyond the total returns an empty list, not an error.

**Preconditions:** Fewer than 100 agents exist.

**Steps:**
1. Send `GET /api/v1/agents?page=999`.

**Expected Result:** HTTP 200. Data array is empty. Pagination object still shows correct total and total_pages.

---

### PAGE-05: Pagination works on all list endpoints

**Description:** All list endpoints (teams, agents, projects) support pagination.

**Preconditions:** Multiple entities of each type exist.

**Steps:**
1. Send `GET /api/v1/teams?page=1&per_page=1`.
2. Send `GET /api/v1/agents?page=1&per_page=1`.
3. Send `GET /api/v1/projects?page=1&per_page=1`.

**Expected Result:** All three responses include correctly formed pagination objects.

---

## Category 13: Error Response Format (ERR)

### ERR-01: Consistent error JSON structure

**Description:** All errors must return the standardized error format.

**Preconditions:** None.

**Steps:**
1. Send a request that triggers a 401 (missing API key).
2. Send a request that triggers a 404 (nonexistent resource).
3. Send a request that triggers a 409 (duplicate slug).
4. Send a request that triggers a 422 (invalid field value).

**Expected Result:** All error responses follow the format:
```json
{
  "error": {
    "code": "<ERROR_CODE>",
    "message": "<human readable message>",
    "details": {}
  }
}
```

---

### ERR-02: Error messages do not leak internal details

**Description:** Error messages should be helpful but not expose database internals, stack traces, or SQL.

**Preconditions:** None.

**Steps:**
1. Send a malformed JSON body to any POST endpoint.
2. Send a request that causes a constraint violation.

**Expected Result:** Error messages describe the problem in user-facing terms. No stack traces, SQL queries, table names, or internal paths are exposed.

---

### ERR-03: Invalid JSON body returns 400

**Description:** Malformed request bodies must be handled gracefully.

**Preconditions:** None.

**Steps:**
1. Send `POST /api/v1/agents` with body `{this is not json}`.
2. Send `POST /api/v1/agents` with Content-Type: application/json but empty body.

**Expected Result:** HTTP 400. Clear error message about invalid JSON.

---

## Category 14: Nautilus Team Migration (MIG)

### MIG-01: Seed script creates the Hands-On Analytics org

**Description:** The migration seed script creates the org with the sponsor's personal statement.

**Preconditions:** Database is fresh (or script is idempotent).

**Steps:**
1. Run the seed script.
2. Send `GET /api/v1/orgs/hands-on-analytics`.

**Expected Result:** Org exists with name "Hands-On Analytics" and the sponsor's full personal statement populated.

---

### MIG-02: Seed script creates all eight evaluation dimensions

**Description:** The sponsor's evaluation framework is seeded.

**Preconditions:** Seed script has been run.

**Steps:**
1. Send `GET /api/v1/orgs/hands-on-analytics/dimensions`.

**Expected Result:** Eight evaluation dimensions are returned, each with name, description, and correct sort_order.

---

### MIG-03: Seed script creates the Nautilus team

**Description:** The team entity is created and linked to the org.

**Preconditions:** Seed script has been run.

**Steps:**
1. Send `GET /api/v1/teams/nautilus`.

**Expected Result:** Team exists with name "Nautilus", slug "nautilus", status "active", and linked to the Hands-On Analytics org.

---

### MIG-04: Seed script creates all Nautilus agents with correct identity data

**Description:** Each agent is created with identity fields populated from their markdown source files. This is the critical migration validation.

**Preconditions:** Seed script has been run.

**Steps:**
1. Send `GET /api/v1/agents/maya-ra`.
2. Send `GET /api/v1/agents/dante-tl` (or whatever Dante's slug is).
3. Send `GET /api/v1/agents/frank-qa`.
4. Repeat for all eight team agents: Maya, Dante, Lena, Nadia, Chris, Sofia, Frank, Quinn.

**Expected Result:** Each agent exists with:
- Correct name, slug, role
- agent_type = "team_member"
- team_id pointing to the Nautilus team
- persona field populated (content should match or be derived from the persona.md files)
- responsibilities field populated (from responsibilities.md)
- relationships field populated (from relationships.md) or null if the source was empty
- understanding field populated (from understanding.md) or null if the source was empty
- status = "active"

---

### MIG-05: Seed script creates Cloud Architect as standalone specialist

**Description:** The Cloud Architect is an org-level specialist, not a team member.

**Preconditions:** Seed script has been run.

**Steps:**
1. Send `GET /api/v1/agents/cloud-architect` (or whatever the slug is).

**Expected Result:** Agent exists with agent_type = "standalone_specialist", team_id = null, and relevant identity fields populated.

---

### MIG-06: Seed script creates Crucible project reference

**Description:** The TeamForge project (codenamed Crucible) is seeded as a project reference.

**Preconditions:** Seed script has been run.

**Steps:**
1. Send `GET /api/v1/projects/crucible`.

**Expected Result:** Project reference exists with name "TeamForge" (or "Crucible"), slug "crucible", and a description.

---

### MIG-07: Seed script connects Nautilus to Crucible project

**Description:** The team-project connection is established during seeding.

**Preconditions:** Seed script has been run.

**Steps:**
1. Send `GET /api/v1/teams/nautilus`.

**Expected Result:** The team's active project connections include the Crucible project.

---

### MIG-08: Seed script is idempotent

**Description:** Running the seed script multiple times must not create duplicate data or fail.

**Preconditions:** Seed script has been run once.

**Steps:**
1. Run the seed script a second time.
2. Send `GET /api/v1/agents` and count agents.
3. Send `GET /api/v1/teams` and count teams.
4. Send `GET /api/v1/orgs/hands-on-analytics/dimensions` and count dimensions.

**Expected Result:** No duplicate orgs, teams, agents, dimensions, or project references. Counts are identical to after the first run. No errors during the second run.

---

### MIG-09: Seed script generates a working API key

**Description:** The seed script must produce at least one API key so the API can be used immediately after seeding.

**Preconditions:** Database is fresh.

**Steps:**
1. Run the seed script.
2. Capture the API key output from the script (displayed once).
3. Use that key to send `GET /api/v1/orgs/hands-on-analytics`.

**Expected Result:** The request succeeds with HTTP 200. The API key correctly resolves to the Hands-On Analytics org.

---

## Category 15: Green Cheese Test -- Wave 1 Portion (GCT)

The full Green Cheese Test spans Waves 1-3. These cases validate the Wave 1 prerequisite: can we store and retrieve the data structures that experience capture will use?

### GCT-01: Experience entries table exists with correct schema

**Description:** The experience_entries table must exist in Wave 1, even though the write/query endpoints are Wave 2.

**Preconditions:** Schema migration has been applied.

**Steps:**
1. Connect to the database directly.
2. Describe the experience_entries table.

**Expected Result:** Table exists with columns: id (UUID), org_id (FK), agent_id (FK), team_id (FK, nullable), project_ref_id (FK, nullable), observation_type (VARCHAR), body (TEXT), embedding (vector(768)), created_at (TIMESTAMPTZ).

---

### GCT-02: Experience entry can be inserted with all fields

**Description:** The table accepts a fully populated experience entry (testing via direct database insert since Wave 1 has no API endpoint).

**Preconditions:** An agent, team, and project reference exist in the database.

**Steps:**
1. Insert an experience_entries row with:
   - agent_id referencing the agent
   - team_id referencing the team
   - project_ref_id referencing the project
   - observation_type = 'lesson'
   - body = 'The moon is made of green cheese. That will be our UAT memory.'
   - embedding = NULL (no embedding engine yet)

**Expected Result:** Row inserts successfully. All foreign key constraints are satisfied. The row is queryable.

---

### GCT-03: Experience entry can be inserted with minimal fields

**Description:** Team and project context are nullable (an observation might not have a specific project context).

**Preconditions:** An agent exists.

**Steps:**
1. Insert an experience_entries row with team_id = NULL and project_ref_id = NULL.

**Expected Result:** Row inserts successfully. Nullable fields accept NULL.

---

### GCT-04: Experience entries are org-scoped

**Description:** Experience entries carry org_id for multi-tenant isolation.

**Preconditions:** Two orgs exist. Each has an agent.

**Steps:**
1. Insert an experience entry for Org A's agent.
2. Query experience_entries WHERE org_id = Org B's ID.

**Expected Result:** Org B's query returns zero rows. The entry is only visible within Org A's scope.

---

### GCT-05: Experience entry supports different observation types

**Description:** The observation_type field supports the defined vocabulary.

**Preconditions:** Agent exists.

**Steps:**
1. Insert experience entries with observation_type values: 'lesson', 'pattern', 'relationship_note', 'heuristic', 'decision'.

**Expected Result:** All five inserts succeed. Each observation_type is stored correctly.

---

### GCT-06: Vector column accepts embedding data

**Description:** The vector(768) column must accept properly formatted vector data when embeddings are generated (Wave 2).

**Preconditions:** pgvector extension is enabled.

**Steps:**
1. Insert an experience_entries row with a 768-dimensional vector in the embedding column (e.g., a dummy vector of 768 float values).

**Expected Result:** Row inserts successfully. The vector data is stored and retrievable.

---

### GCT-07: Review entries table exists with correct schema

**Description:** The review_entries table is another Wave 1 placeholder for Wave 2 functionality.

**Preconditions:** Schema migration has been applied.

**Steps:**
1. Connect to the database and describe the review_entries table.

**Expected Result:** Table exists with columns: id, org_id, subject_agent_id, reviewer_agent_id (nullable), reviewer_type, project_ref_id (nullable), scores (JSONB), narrative (TEXT, nullable), narrative_embedding (vector(768)), created_at.

---

## Category 16: Edge Cases and Boundary Conditions (EDGE)

### EDGE-01: Slug format validation (kebab-case)

**Description:** Slugs should conform to kebab-case format.

**Preconditions:** Org exists.

**Steps:**
1. Send `POST /api/v1/agents` with slug "Maya RA" (spaces).
2. Send `POST /api/v1/agents` with slug "MAYA-RA" (uppercase).
3. Send `POST /api/v1/agents` with slug "maya_ra" (underscores).
4. Send `POST /api/v1/agents` with slug "" (empty string).

**Expected Result:** At minimum, empty string is rejected. The system should either reject non-kebab-case slugs (400/422) or normalize them. The expected behavior should be consistent and documented.

---

### EDGE-02: Very long field values

**Description:** Fields have defined max lengths (VARCHAR(255), VARCHAR(100)). Exceeding them should fail gracefully.

**Preconditions:** Org exists.

**Steps:**
1. Send `POST /api/v1/teams` with a name that is 256 characters long.
2. Send `POST /api/v1/teams` with a slug that is 101 characters long.

**Expected Result:** HTTP 400 or 422 with clear validation error. Not a 500 server error.

---

### EDGE-03: Agent with extremely long persona text

**Description:** The persona field is TEXT (unlimited length). Large values should be handled.

**Preconditions:** Org exists.

**Steps:**
1. Send `POST /api/v1/agents` with a persona field containing 50,000 characters of text.

**Expected Result:** The agent is created successfully. The full text is stored and retrievable.

---

### EDGE-04: Unicode and special characters in text fields

**Description:** Names, descriptions, and text content must handle international characters.

**Preconditions:** Org exists.

**Steps:**
1. Create a team with name containing unicode: "Team Alpha (a-Team)".
2. Create an agent with persona containing special characters, line breaks, and accented characters.

**Expected Result:** All values are stored and retrieved without corruption or encoding errors.

---

### EDGE-05: Concurrent duplicate slug creation

**Description:** Two simultaneous requests to create entities with the same slug should not both succeed.

**Preconditions:** Org exists. No agent with slug "test-agent" exists.

**Steps:**
1. Send two simultaneous `POST /api/v1/agents` requests with slug "test-agent".

**Expected Result:** Exactly one request succeeds (HTTP 201). The other returns HTTP 409. The database has exactly one agent with that slug.

---

### EDGE-06: Deactivated agent does not appear in team roster

**Description:** When an agent is deactivated, they should not show as part of an active team roster.

**Preconditions:** Agent is on a team and then deactivated.

**Steps:**
1. Get the team roster before deactivation -- agent is present.
2. Deactivate the agent.
3. Get the team roster after deactivation.

**Expected Result:** The deactivated agent does not appear in the default team roster returned by `GET /api/v1/teams/<team>`. The team's active member count is reduced by one.

---

### EDGE-07: Deactivated agent still directly accessible

**Description:** Even though deactivated agents are filtered from listings, direct GET by slug or UUID still works.

**Preconditions:** Agent is deactivated.

**Steps:**
1. Send `GET /api/v1/agents/<deactivated-agent-slug>`.

**Expected Result:** HTTP 200. The agent is returned with status = "inactive" and all data intact.

---

### EDGE-08: Agent scores reference correct dimensions after dimension rename

**Description:** Renaming a dimension should not break the linkage to existing scores.

**Preconditions:** A dimension exists with scores. The dimension is renamed.

**Steps:**
1. Create a dimension "Honesty".
2. Create an agent_scores entry referencing that dimension.
3. Rename the dimension to "Honesty & Transparency".
4. Get the agent -- check current_scores.

**Expected Result:** The score entry still references the correct dimension. The dimension_name in the agent's current_scores reflects the new name.

---

### EDGE-09: Activate an already active agent

**Description:** Activating an agent that is already active should be a no-op, not an error.

**Preconditions:** Agent is already active.

**Steps:**
1. Send `PATCH /api/v1/agents/maya-ra/activate`.

**Expected Result:** HTTP 200. Agent remains active. No error. This is idempotent.

---

### EDGE-10: Deactivate an already inactive agent

**Description:** Deactivating an already inactive agent should be a no-op.

**Preconditions:** Agent is already inactive.

**Steps:**
1. Send `PATCH /api/v1/agents/maya-ra/deactivate`.

**Expected Result:** HTTP 200. Agent remains inactive. No error.

---

### EDGE-11: Request with unsupported HTTP method

**Description:** Methods that are not defined for a route should be handled.

**Preconditions:** None.

**Steps:**
1. Send `PUT /api/v1/agents/maya-ra` (PUT is not defined; PATCH is used).
2. Send `DELETE /api/v1/agents/maya-ra` (DELETE does not exist for agents).

**Expected Result:** HTTP 405 (Method Not Allowed) for each.

---

### EDGE-12: Filter combinations on agent list

**Description:** Combining filters should work correctly.

**Preconditions:** A mix of agents: team_members on a team, unassigned team_members, standalone specialists.

**Steps:**
1. Send `GET /api/v1/agents?agent_type=team_member&unassigned=true`.
2. Send `GET /api/v1/agents?agent_type=standalone_specialist&team_slug=nautilus`.

**Expected Result:** Step 1 returns only team_member agents with no team assignment. Step 2 returns an empty list (standalone specialists are never on a team).

---

### EDGE-13: Pagination with filters

**Description:** Pagination and filters must work together correctly.

**Preconditions:** Multiple team_member agents on team "nautilus".

**Steps:**
1. Send `GET /api/v1/agents?team_slug=nautilus&per_page=2&page=1`.
2. Note the total from pagination.

**Expected Result:** The paginated result correctly reflects the filtered count, not the total agent count.

---

## Category 17: Full Entity Lifecycle (LIFE)

### LIFE-01: Complete agent lifecycle

**Description:** Exercise the full lifecycle: create, read, update, assign to team, deactivate, reactivate.

**Preconditions:** Org and team exist.

**Steps:**
1. Create agent with no team (POST /api/v1/agents).
2. Verify agent appears in unassigned list.
3. Add agent to team (POST /api/v1/teams/nautilus/members).
4. Verify agent appears in team roster.
5. Update agent persona (PATCH /api/v1/agents/<slug>).
6. Verify updated persona.
7. Remove agent from team (DELETE /api/v1/teams/nautilus/members/<slug>).
8. Verify agent is unassigned again.
9. Deactivate agent (PATCH /api/v1/agents/<slug>/deactivate).
10. Verify agent excluded from default list but accessible directly.
11. Reactivate agent (PATCH /api/v1/agents/<slug>/activate).
12. Verify agent appears in default list again.

**Expected Result:** Every step succeeds. Data integrity is maintained throughout. No data is lost at any transition point.

---

### LIFE-02: Complete team lifecycle

**Description:** Exercise the full team lifecycle: create, add members, connect to project, deactivate, reactivate.

**Preconditions:** Org, agents, and project reference exist.

**Steps:**
1. Create team (POST /api/v1/teams).
2. Add agents to team.
3. Create a norm for the team.
4. Connect team to project.
5. Verify GET team shows roster, norm, and project connection.
6. Remove all agents from team.
7. Deactivate team.
8. Verify team excluded from default list.
9. Reactivate team.
10. Add agents back.
11. Verify team is fully functional again.

**Expected Result:** All operations succeed. Norms and project connection history are preserved through deactivation and reactivation.

---

### LIFE-03: Complete project lifecycle

**Description:** Project references can be created, connected, disconnected, and deleted.

**Preconditions:** Org and team exist.

**Steps:**
1. Create project reference.
2. Connect team to project.
3. Disconnect team from project.
4. Verify connection history is preserved.
5. Delete project reference (now that no active connections exist).
6. Verify project is gone.

**Expected Result:** All operations succeed. Connection history exists even after project deletion (or the delete fails if history references are enforced -- either behavior is acceptable as long as it is consistent).

---

---

## Summary

| Category | Count | Focus |
|----------|-------|-------|
| Infrastructure (INFRA) | 4 | Service health, HTTPS, pgvector |
| Authentication (AUTH) | 8 | API key security, org isolation |
| Organization CRUD (ORG) | 9 | Org creation, update, immutability |
| Evaluation Dimensions (DIM) | 7 | Dimension CRUD, deletion protection |
| Teams (TEAM) | 12 | Team CRUD, deactivation, no-delete |
| Agents (AGENT) | 22 | Agent CRUD, identity, types, filters |
| Team Composition (COMP) | 7 | Membership rules, cross-org, specialists |
| Projects & Connections (PROJ) | 12 | Projects, connections, history |
| Team Norms (NORM) | 3 | Norm creation and retrieval |
| Org Suggested Norms (ONORM) | 2 | Org-level norm promotion |
| Data Integrity (INTEG) | 8 | FK constraints, org scoping, preservation |
| Pagination (PAGE) | 5 | Defaults, limits, edge pages |
| Error Format (ERR) | 3 | Consistent errors, no leaks |
| Migration (MIG) | 9 | Seed script, Nautilus team, idempotency |
| Green Cheese Test - Wave 1 (GCT) | 7 | Experience/review schema readiness |
| Edge Cases (EDGE) | 13 | Slugs, unicode, concurrency, filters |
| Full Lifecycle (LIFE) | 3 | End-to-end entity workflows |

**Total: 134 UAT test cases**

---

*Frank (QA) | 2026-03-15 | Status: Awaiting sponsor review before execution*
