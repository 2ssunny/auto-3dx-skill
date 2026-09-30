# Upstream SDK sync record

This is maintenance evidence for the skill. At runtime, the installed SDK is
authoritative; a version match is not required. The machine-readable companion
is [compatibility.json](../compatibility.json).

## Skill 2.1 review against SDK v1.0.0, 2026-10-01

| Field | Reviewed state |
|---|---|
| Skill revision | 2.1.0 (additive: v1 capabilities on the v2 operating contract) |
| SDK repository | `2ssunny/auto-3dx`, local read-only checkout |
| SDK branch and exact HEAD | `feat/v1-functional-completeness`, `e39b63d381a5e1d6483f5f48f9f5c9bd3d5c2039` (pushed; verified identical on the remote) |
| SDK code baseline | `08df6b9`. `38e957f` changes three docstring lines in `bodies.py`; `e39b63d` changes only the `pyproject.toml` version on top of it |
| SDK package version | `1.0.0` in `pyproject.toml` (not tagged when reviewed) |
| Previous skill review | `d8bf819` (Skill 2.0.0). Since the PR #4 merge `53625b3` nothing public was removed. Existing calls changed behavior in three ways: `part.geometry.edges()` (and so `find_edge`) drops sketch profile edges; `create_hole` always writes the hole type (simple unless `head=`), because CATIA carries it over; a positioned hole can now raise `HolePlacementMismatchError` instead of silently landing elsewhere |
| Static evidence (rerun here) | 1359 unit tests passed at `08df6b9`, Conda `auto-3dx`, Python 3.11.16 |
| Release check (reported) | By the SDK v1 session at `e39b63d`: 1359 unit passed, ruff clean, mypy at its 40-error baseline with none new; an isolated wheel installs into a fresh venv as `1.0.0` and imports, and its 43 `auto_3dx/` files are byte-identical to the `38e957f` wheel |
| Live evidence (reported) | By the SDK v1 session, at `08df6b9`, on a disposable Part with Conda Python 3.11.16 and pywin32 312: `tests/integration/test_v1_live.py` 16/16 (15 in one run, the human edge-click stage separately with `AUTO3DX_HUMAN=1`), Phase 5 live regression 11/11, no Save/PLMPropagate/export. This result is not yet recorded in SDK documentation |

The SDK README and `docs/` were unchanged across this delta; the review used
the public implementation and docstrings under `src/auto_3dx`, the v1
micro-probes `scripts/probes/47a`–`47o`, the unit tests, and the staged live
acceptance suite. This skill review did not operate CATIA.

### What changed in agent decisions

- `part.selection` reads "the element the user selected" into ordinary SDK
  handles with typed count, kind and ownership refusals, and highlights
  elements for the user without touching the model. Raw CATIA `Selection`
  stays off limits.
- True face-edge adjacency is available (`adjacent_to`, `edges_of`,
  `faces_of`), measured against the bounded face. `on_plane_of` remains
  coplanarity only. Consumed-sketch profile edges are identified
  (`from_sketch`, `solid()`), and `part.geometry` edge finders drop them.
- Holes gain `up_to_next`, counterbored and countersunk heads, and origin
  read-back with `HolePlacementMismatchError`. Reversal stays refused.
- `rectangle(..., constraints="fully")` is a drivable fully constrained
  rectangle by degree-of-freedom count; the other levels stay four free lines.
- `part.geometry.offset_plane` offsets from a planar face on a material side;
  `plane.origin`/`normal` answer after a rebuild.
- `part.inspect.feature(name)` / `sketch(name)` read one object without a
  topology search. Circular Pattern `full_circle` replaces reliance on CATIA's
  ignored crown flag.

### Validator coverage change

The count rose from **254** to **428** checked references (63 explicit
symbols, 365 example references). Measured on `main`'s documents:

| Documents | Checker | Explicit | Example refs |
|---|---|---|---|
| `main` (2.0.0) | 2.0.0 checker | 26 | 228 |
| `main` (2.0.0) | 2.1.0 checker | 63 | 236 |
| 2.1.0 | 2.1.0 checker | 63 | 365 |

- **+37 explicit symbols**: the SDK v1 entry points listed in
  `SDK_V1_PUBLIC_SYMBOLS`.
- **+8 example references on unchanged documents**: the checker now resolves
  forward return annotations the SDK imports only under `TYPE_CHECKING` (for
  example `Body.features`, `Sketch.rectangle`, `Inspector.feature`) against
  the loaded auto_3dx classes. Before this, calls through `body.features.*`
  were not signature-checked. A deliberately misspelled keyword or member on
  each new v1 path was confirmed to fail.
- **+129 example references**: the new and revised v1 examples.

## Skill v2 review, 2026-09-27 (finalized 2026-09-28)

| Field | Reviewed state |
|---|---|
| Skill revision | v2 (Phase 5 intent API operating contract) |
| SDK repository | `2ssunny/auto-3dx`, local read-only checkout |
| SDK branch and exact HEAD | `feat/phase5-high-level-api`, `d8bf8195e8108fd5b581accd9e770c6bb3c33b65` (pushed) |
| SDK package version | `0.1.0` in `pyproject.toml` |
| SDK code baseline | `3342a4b` (Phase 5 implementation and live acceptance). `d8bf819` changes only README and `docs/`; `src`, `tests`, `examples`, `scripts` and `pyproject.toml` are identical, so no public API behavior changed after Skill v2 validation |
| Evidence | `docs/phase5-api-design.md` reports 11/11 Phase 5 staged live tests and 73 passed, 6 skipped in the full live suite on `B428_Cloud` |
| Previous skill review | Phase 4 SDK commit `6a74d07` |

The review covered SDK README, `docs/api-design.md`,
`docs/phase5-api-design.md`, `docs/conventions.md`, `docs/status.md`, public
implementation/docstrings under `src/auto_3dx`, `examples/intent_api.py`,
`examples/build_part.py`, and Phase 5 unit/live test names and contract.
The live results are SDK-reported evidence. This skill review did not operate
CATIA or rerun live tests.

The first v2 draft was reviewed at `3342a4b`. The SDK then added only the
documentation commit `d8bf819`, so the Skill's public API guidance needed no
signature or capability correction. That commit resolves the historical SDK
passages that earlier conflicted with Phase 5: README and capabilities samples
now select faces and edges by measured facts or `part.geometry.find_*` instead
of snapshot order and re-find after updates, and the older "line coordinates
unavailable" and "Circular Pattern is Z-only" statements are marked as Phase
2–4 history pointing to the Phase 5 correction.

### What changed in agent decisions (v2)

- Prefer the Level 3 public intent API for common feature creation, sketch
  primitives, semantic finding, properties, and targeted facts. Level 2 stays
  the supported fallback when intent needs a more precise composition.
- `sketch.geometry()` and `SketchElement.geometry()` read back verified geometry
  after the edition closes. Planar-face sketches expose a frame for coordinate
  conversion. Rectangle constraints are `none`, `orientation`, or `dimensioned`;
  none proves full constraint.
- A Hole can be positioned and can be blind or through-all, with explicit
  diameter and verified flat/V bottom. The SDK writes limit behavior explicitly
  because CATIA carries defaults between holes.
- Circular Pattern axes X/Y/Z, cylindrical Face, and linear Edge are verified.
  Complete-crown mode is not. `on_plane_of(face)` is coplanarity, not adjacency.
- `part.inspect.facts(...)` avoids topology enumeration for routine checks. The
  Phase 5 test measured 0.038 s for targeted facts versus 1–3.5 s for summary
  on its live Part. These are evidence from that setup, not performance promises.

### Validator coverage audit (v2)

The historical validator's **216** checks came from 214 names in the old
`references/examples.md` and two in `references/part-design.md`. The first v2
draft reduced the example file to common high-level workflows: **123** checks
comprised 81 example names, 14 high-level reference names, two Part Design
names, and 26 explicit Phase 5 symbols. This was a real loss of executable
coverage for supported Level 2 operations, not a change in the checker.

The final v2 pass restored focused advanced Level 2 examples for detailed
inspection, parameters/formula dependencies, measurements and Pocket direction,
update recovery, planes and history placement, sketch rediscovery, multi-body
booleans, patterns, and suppression. The audit also found that forward return
annotations on `EdgeSnapshot.query()` and `FaceSnapshot.query()` prevented the
checker from following chained query calls. The validator now resolves those
public query types and their fluent return type. That improvement would raise
the old examples' count from 216 to 228 under the new checker.

The final count against SDK `d8bf819` (code identical to `3342a4b`) is **254**: 212 names in
`references/examples.md`, 14 in `references/high-level-api.md`, two in
`references/part-design.md`, and 26 explicit Phase 5 symbols. It is a count of
checked references, including repeated uses, not a count of distinct API
capabilities. The restored examples protect useful call signatures without
restoring stale Phase 4 claims.

## Next sync

Compare the SDK implementation and public docs since the reviewed commit;
verify the exact new HEAD, that it is fetchable from the remote, and any local
SDK modifications. Update only affected guidance and examples, then run
`scripts/validate_skill.py` in the default interpreter and a documented SDK
development interpreter. Update `compatibility.json` with the reviewed SDK
commit and the actual validation result. A validation skip is not an API pass.
