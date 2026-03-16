# Spec: core-crud-api

**Parent Proposal:** wave1-foundation
**Author:** Maya (RA)
**Status:** Draft -- pending TL feasibility review

---

## What This Spec Covers

RESTful API endpoints for creating, reading, updating, listing, and deleting entities defined in the `org-team-agent-schema` spec. This is the foundational API surface. Workflow endpoints (experience capture, review submission, norm approval) are Wave 2.

## API Conventions

### Base URL

`/api/v1`

All endpoints are prefixed with a version. Version bumps are future -- v1 is all that exists in Phase 1.

### Authentication

Every request must include an API key in the header:

```
X-API-Key: <org-api-key>
```

The API key identifies the org. All data operations are scoped to that org. No API key means 401. Invalid API key means 401. API key associated with a different org than the requested resource means 403.

### Request/Response Format

- All request bodies are JSON (`Content-Type: application/json`)
- All response bodies are JSON
- Timestamps are ISO 8601 with timezone (e.g., `2026-03-15T14:30:00Z`)
- UUIDs are lowercase hyphenated (e.g., `550e8400-e29b-41d4-a716-446655440000`)

### Error Format

All errors return a consistent JSON structure:

```json
{
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "Agent with slug 'maya-ra' not found.",
    "details": {}
  }
}
```

HTTP status codes follow standard conventions: 400 (bad request), 401 (unauthorized), 403 (forbidden), 404 (not found), 409 (conflict), 422 (validation error), 500 (server error).

### Pagination

List endpoints return paginated results:

```json
{
  "data": [...],
  "pagination": {
    "total": 42,
    "page": 1,
    "per_page": 20,
    "total_pages": 3
  }
}
```

Query parameters: `page` (default 1), `per_page` (default 20, max 100).

### Slug Conventions

Entities that support slug-based lookup (orgs, teams, agents, projects) can be referenced by either UUID or slug in URL paths. The API accepts both:

- `GET /api/v1/agents/550e8400-e29b-41d4-a716-446655440000`
- `GET /api/v1/agents/maya-ra`

Slugs are kebab-case, unique within their org scope.

---

## Endpoints

### Organizations

**POST /api/v1/orgs**

Create a new organization. This is an admin-level operation -- in Phase 1, it is available to anyone with a valid API key. Future RBAC will restrict this.

Request body:
```json
{
  "name": "Nautilus",
  "slug": "nautilus",
  "personal_statement": "Be honest. If you don't know, say you don't know..."
}
```

Response: 201, full org object.

**GET /api/v1/orgs/:id_or_slug**

Get the org associated with the current API key. In Phase 1, the API key maps to exactly one org, so this endpoint returns that org's data. The id_or_slug parameter is validated against the API key's org.

Response includes: org fields, evaluation_dimensions array, suggested_norms array.

**PATCH /api/v1/orgs/:id_or_slug**

Update org fields. Supports partial updates (only send fields being changed).

Updatable fields: name, personal_statement.

Slug is immutable after creation.

---

### Evaluation Dimensions

**POST /api/v1/orgs/:org/dimensions**

Create an evaluation dimension for the org.

Request body:
```json
{
  "name": "Honesty & Transparency",
  "description": "Presents uncertainty honestly, shows reasoning, surfaces problems early",
  "sort_order": 1
}
```

Response: 201.

**GET /api/v1/orgs/:org/dimensions**

List all evaluation dimensions for the org. Not paginated (expected to be a small set).

**PATCH /api/v1/orgs/:org/dimensions/:id**

Update a dimension. Name and description are updatable. Sort order is updatable.

**DELETE /api/v1/orgs/:org/dimensions/:id**

Delete a dimension. Returns 409 if any agent_scores reference this dimension. Dimensions with score history cannot be deleted -- they can only be renamed.

---

### Teams

**POST /api/v1/teams**

Create a team within the org.

Request body:
```json
{
  "name": "Nautilus",
  "slug": "nautilus",
  "description": "Primary development team"
}
```

Response: 201, full team object.

**GET /api/v1/teams/:id_or_slug**

Get a team. Response includes: team fields, roster (array of agent summaries), active project connections, team norms.

**PATCH /api/v1/teams/:id_or_slug**

Update team fields. Name and description are updatable. Slug is immutable.

**GET /api/v1/teams**

List all teams in the org. Supports pagination. Optional filters: none in Wave 1 (future: by project connection status).

**Teams are never deleted.** A team's history, norms, and accumulated culture are persistent. Teams that are no longer active are deactivated, not destroyed.

**PATCH /api/v1/teams/:id_or_slug/deactivate**

Deactivate a team. Sets status to 'inactive'. The team retains all norms, history, and project connection records. Agents on the team must be reassigned or unassigned first — returns 409 if the team still has active members.

**PATCH /api/v1/teams/:id_or_slug/activate**

Reactivate a previously deactivated team.

Deactivated teams are excluded from `GET /api/v1/teams` by default. Pass `?include_inactive=true` to include them.

---

### Agents

**POST /api/v1/agents**

Create an agent within the org.

Request body:
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
  "team_id": null
}
```

team_id is optional. If omitted or null, the agent is created without team assignment (hired for growth or standalone specialist).

Response: 201, full agent object.

**GET /api/v1/agents/:id_or_slug**

Get an agent. Response includes: agent fields, current_scores (array of dimension scores), team membership (if any).

The current_scores array returns one entry per evaluation dimension:
```json
{
  "current_scores": [
    {
      "dimension_id": "...",
      "dimension_name": "Honesty & Transparency",
      "current_score": 4.2,
      "rolling_average": 4.0,
      "review_count": 3,
      "last_reviewed_at": "2026-03-10T00:00:00Z"
    },
    {
      "dimension_id": "...",
      "dimension_name": "Accountability",
      "current_score": null,
      "rolling_average": null,
      "review_count": 0,
      "last_reviewed_at": null
    }
  ]
}
```

Dimensions with no reviews return null scores, not default values.

**PATCH /api/v1/agents/:id_or_slug**

Update agent identity fields. Updatable fields: name, persona, responsibilities, understanding, relationships, role.

agent_type is immutable after creation.
slug is immutable after creation.
team_id is NOT updatable through this endpoint -- use the team composition endpoints.

**GET /api/v1/agents**

List agents in the org. Supports pagination.

Filters (query parameters):
- `team_id` or `team_slug` -- agents on a specific team
- `unassigned=true` -- agents with no team
- `agent_type=team_member|standalone_specialist`

**Agents are never deleted.** Agent identities are sacred — they are persistent identities that accumulate experience and growth over time. Deleting an agent would destroy accumulated value and violate the core mission.

**PATCH /api/v1/agents/:id_or_slug/deactivate**

Deactivate an agent. Sets status to 'inactive'. The agent retains all identity, experience, and score data. They no longer appear in active team rosters or default agent listings, but can be reactivated.

**PATCH /api/v1/agents/:id_or_slug/activate**

Reactivate a previously deactivated agent. Sets status to 'active'.

Deactivated agents are excluded from `GET /api/v1/agents` by default. Pass `?include_inactive=true` to include them.

---

### Project References

**POST /api/v1/projects**

Create a project reference.

Request body:
```json
{
  "name": "TeamForge",
  "slug": "crucible",
  "description": "Persistent agent team service"
}
```

Response: 201.

**GET /api/v1/projects/:id_or_slug**

Get a project reference. Response includes: project fields, connected_teams (array of teams currently connected).

**PATCH /api/v1/projects/:id_or_slug**

Update project reference fields. Name and description updatable. Slug immutable.

**GET /api/v1/projects**

List project references in the org. Supports pagination.

**DELETE /api/v1/projects/:id_or_slug**

Delete a project reference. Returns 409 if any teams are currently connected. Disconnect teams first.

---

### Team Composition

**POST /api/v1/teams/:team/members**

Add an agent to a team.

Request body:
```json
{
  "agent_id": "..."
}
```

Validations:
- Agent must be in the same org as the team
- Agent must not already be on another team (an agent belongs to at most one team)
- Agent must have agent_type = 'team_member' (standalone specialists cannot be added to teams)

Response: 200, updated team roster.

**DELETE /api/v1/teams/:team/members/:agent_id_or_slug**

Remove an agent from a team. Sets the agent's team_id to NULL. The agent is not deleted -- just unassigned.

---

### Team-Project Connections

**POST /api/v1/teams/:team/projects**

Connect a team to a project.

Request body:
```json
{
  "project_id": "..."
}
```

Validations:
- Team and project must be in the same org
- A team can be connected to multiple projects simultaneously
- Duplicate active connections are rejected (409) -- same team already connected to same project with disconnected_at = NULL

Response: 201, connection record.

**DELETE /api/v1/teams/:team/projects/:project_id_or_slug**

Disconnect a team from a project. Sets disconnected_at on the active connection record. Does not delete the record (preserves history).

---

### Health

**GET /api/v1/health**

No authentication required. Returns service health.

```json
{
  "status": "healthy",
  "database": "connected",
  "timestamp": "2026-03-15T14:30:00Z"
}
```

---

## What This Spec Does NOT Cover

- Experience capture endpoints (Wave 2)
- Performance review submission and score computation endpoints (Wave 2)
- Norm proposal/approval workflow endpoints (Wave 2)
- Experience query/search endpoints (Wave 2)
- Batch operations (future, if needed)
- Webhook notifications (future, if needed)
- Rate limiting (future -- not needed for Phase 1 internal use)

---

## Acceptance Criteria

1. All CRUD endpoints return correct HTTP status codes for success and error cases.
2. API key authentication is enforced on all endpoints except health check.
3. All data operations are scoped to the org associated with the API key.
4. Invalid or missing API key returns 401.
5. Requesting a resource belonging to a different org returns 403.
6. Creating an entity with a duplicate slug within the same org returns 409.
7. Agents cannot be deleted — no DELETE endpoint exists for agents. Deactivation sets status to 'inactive'.
8. Deactivating a team with active members returns 409.
9. Deleting a dimension with existing scores returns 409.
10. Adding a standalone specialist to a team returns 422.
11. GET agent returns current_scores array with null values for unreviewed dimensions.
12. Deactivated agents are excluded from default listings but included with `?include_inactive=true`.
13. Deactivated teams are excluded from default listings but included with `?include_inactive=true`.
12. GET team returns the full roster, active project connections, and team norms.
13. Disconnecting a team from a project preserves the connection history (disconnected_at is set, row is not deleted).
14. Pagination works correctly on all list endpoints.
15. All timestamps are returned in ISO 8601 format with timezone.
