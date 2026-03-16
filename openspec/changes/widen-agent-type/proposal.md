# Widen Agent Type Column

**Status:** Complete (retroactive)
**Date:** 2026-03-15
**Author:** Dante (TL)

## Problem

The `agents.agent_type` column was defined as `VARCHAR(20)` in the Wave 1 schema. The value `"codebase_analyst"` (17 characters) fits, but leaves no headroom for future agent types. A wider column prevents truncation errors without any cost.

## Change

Alembic migration `002_widen_agent_type.py` widens `agents.agent_type` from `VARCHAR(20)` to `VARCHAR(30)`.

## Key Files

- Migration: `/home/cheston_riley/workspace/crucible/api/migrations/versions/002_widen_agent_type.py`

## Impact

Schema-only. No API changes. No data migration. Backward compatible.
