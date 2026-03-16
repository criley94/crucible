# Proposal: Experience Recall Improvements

**Author:** Maya (RA) -- retroactive documentation
**Date:** 2026-03-16
**Status:** Complete -- implemented in CLAUDE.md and seed.md templates
**Parent:** TeamForge Phase 1

---

## Problem Statement

After the initial Wave 3 Claude Code integration, agents were under-querying the experience API. The original spec said agents should query experience "on-demand when you need it," but agents interpreted this conservatively and rarely triggered experience searches during sessions. This meant the team's accumulated knowledge was not being leveraged.

---

## What Was Built

### Strengthened Experience Query Triggers

The experience protocol section in CLAUDE.md and seed.md templates was enhanced with explicit trigger conditions. The original generic instruction ("Query when you have a specific need") was supplemented with concrete triggers:

1. The sponsor asks about preferences, history, or past decisions
2. The sponsor asks a question that could have been discussed before
3. Making a technical or process decision the team may have encountered before
4. The conversation touches team dynamics, relationships, or working style
5. Encountering a familiar pattern or needing cross-project context

### "When in Doubt, QUERY" Heuristic

Added the explicit heuristic: "When in doubt about whether to query, QUERY. An unnecessary search costs a few seconds. A missed recall costs the team a lesson already learned."

This shifts the default from conservative (query only when certain) to aggressive (query unless certain it is unnecessary).

---

## Affected Files

- `/home/cheston_riley/workspace/crucible/CLAUDE.md` -- experience protocol section
- `/home/cheston_riley/workspace/crucible/seed.md` -- CLAUDE.md generation template and agent definition template
- `/home/cheston_riley/workspace/crucible/scripts/provision_team.py` -- CLAUDE.md generation function

All three files contain the strengthened trigger language. The seed.md and provision_team.py templates ensure that newly provisioned teams also get the improved triggers.

---

## Impact

This is a behavioral improvement, not a code change. No API modifications, no schema changes. The improvement is in the instructional text that shapes how agents interact with the existing experience search API.

---

## Note

This work was done as part of the Wave 3.5 provisioning implementation but was not tracked as a separate OpenSpec change at the time. This proposal is retroactive documentation.
