---
name: auto-3dx
description: Use the public auto-3dx Python SDK to inspect or edit an open 3DEXPERIENCE CATIA Part. Applies to live CAD modeling, sketches, Part Design features, semantic topology selection, measurements, and safe recovery; the SDK is authoritative for signatures and mechanics.
---

# auto-3dx — agent operating contract

**Prefer the highest-level public auto-3dx API that precisely expresses the engineering intent.**
Use the composable low-level public API when the intent API cannot express it. Never bypass
either layer with raw COM, private SDK code, topology indices, or descriptor strings during
ordinary CAD work. The installed SDK wins if this skill differs from it; report the drift.

## Start and choose an API

- Use the project's configured 64-bit Python 3.11+ environment on Windows. Confirm
  `auto_3dx` is importable there; do not silently switch interpreters. Attach to an already
  running 3DEXPERIENCE session and an already open Part. The SDK does not create PLM Parts.
- `Catia.attach()` then explicitly choose the target with `catia.part_named(name)` when
  several editors exist. `catia.active_window_title` can help confirm the UI document;
  `active_part()` is suitable only when the target is unambiguous.
- **Level 3, preferred:** `body.features.pad/pocket/hole/fillet/chamfer/circular_pattern`,
  `sketch.rectangle/centered_rectangle/circle`, `part.geometry.*`, `part.inspect.facts(...)`,
  and verified writable feature properties.
- **Level 2, supported fallback:** `part.sketches.create`, `sketch.edit()` and editor methods,
  `part.part_design.create_*`, `part.topology.*`, `snapshot.query()`, explicit setters/getters,
  and `part.measurement.measure()`. Use it for uncommon intent, composition beyond a helper,
  debugging, or a missing Level 3 abstraction. It is not deprecated.
- **Level 1 is off limits for ordinary modeling:** `win32com`, `com3dx`, `com_object`
  mutation, `ShapeFactory`, `Selection`, raw Automation, and private SDK implementation.
  An unsupported public operation is a finding to report, not permission to bypass the SDK.

## Preferred workflow

```text
attach -> select Part explicitly -> cheap targeted inspection -> choose highest applicable
public API -> group deterministic edits -> part.update() -> targeted verification ->
full topology or geometry validation when the task needs it
```

1. Read only the facts needed to establish the baseline, usually
   `part.inspect.facts("up_to_date", "volume")`; check names or body context separately
   when relevant. If the model is already dirty, report that before editing.
2. Choose the body and feature history context. Level 3 `body.features.*` selects its body;
   Level 2 uses `with part.work_in(body):` and, when necessary, `part.work_at(feature)`.
   Rediscover persistent model objects by name in a new process.
3. Complete a logical sketch or deterministic edit group, close any `sketch.edit()` block,
   then call `part.update()`. Mutations and property assignments never implicitly rebuild.
   Rebuild earlier when rebuilt topology is needed for the next selection.
4. Verify the intended effect with targeted facts, property read-back, or a semantic query.
   A successful rebuild alone does not prove a Pocket removed material. Use
   `part.inspect.summary()`, topology snapshots, or full measurement for semantic discovery,
   detailed final validation, failure diagnosis, or an explicit request.

## Geometry and sketch rules

- Prefer `part.geometry.top_face()` for the top face. Its meaning is planar, **unsigned**
  normal parallel to global Z, then highest spatial extreme. A plane normal is not an
  outward solid normal. Never use first face, a face index, a descriptor, or normal sign.
- For a query beyond a finder, use one body-scoped snapshot and compose `snapshot.query()`;
  require `.one()` for a single entity. Reuse a valid snapshot and its measured facts within
  one generation. After a geometry-changing edit, reselect from a fresh snapshot.
- `on_plane_of(face)` means an edge lies on that face's plane. It does **not** prove the edge
  bounds the face; true face-edge adjacency is unsupported.
- A sketch can use an origin/user plane or a planar `Face`. On a face, use `sketch.frame()`
  to convert between global and sketch-local coordinates; the frame origin need not be the
  face centre. `sketch.rectangle(..., constraints="none"|"orientation"|"dimensioned")`
  and `centered_rectangle` are not fully constrained: even `dimensioned` does not create
  corner coincidence constraints. Complete the logical sketch, close the edition, then use
  `sketch.geometry()` or `element.geometry()` for read-back. Do not read geometry in an
  active edit session.

## Update, inspection, and recovery

- Call `part.update()` at a logical boundary, before a dependent topology selection, and
  before update-sensitive verification. Do not update after each sketch line.
- Prefer `part.inspect.facts(...)` for routine checks; it avoids a topology search. Full
  `summary()` and snapshots cost more and should answer a concrete question. Do not treat
  measured Phase 5 timings as universal guarantees.
- Distinguish validation, not found, ambiguity, unsupported capability, stale snapshot,
  update failure, dependency in use, and Automation errors. Fix the cause or refine intent;
  never route around a typed refusal with raw COM. On `PartUpdateError`, inspect
  `error.issues` or `part.inspect.update_issues()` as symptoms, restore the last valid
  reversible value and update again. Remove a newly created invalid feature only when
  rollback is unavailable. Do not delete downstream features to force a rebuild.
- The SDK does not save or export. Tell the user edits remain unsaved. Destructive removal
  needs user intent for the named object; boolean tool bodies are consumed permanently.

## Agent performance traps

Avoid a full summary after every mutation, a fresh topology snapshot when no topology is
needed, a new decision for each deterministic sketch line, update after every entity,
recreating a query within one valid snapshot, raw COM after `UnsupportedOperationError`
or another typed refusal, and repeated source exploration after the API contract is known.

## Read the detail that fits the task

- [High-level API and inspection](references/high-level-api.md): intent calls, properties,
  targeted facts, and Level 2 mappings.
- [Examples](references/examples.md): block, face sketch and Pocket, Hole, edge feature,
  revision, targeted inspection, and low-level fallback.
- [Geometry queries](references/geometry-query.md) and [topology](references/topology.md):
  semantic selection, ownership, staleness, and strict cardinality.
- [Part Design](references/part-design.md), [editing](references/editing.md), and
  [capabilities](references/capabilities.md): feature limits and supported fallback paths.
- [Safety](references/safety.md): typed errors, side effects, recovery, and persistence.
- [Upstream sync](references/upstream-sync.md): exact SDK revision and review evidence.
