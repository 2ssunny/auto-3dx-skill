# Upstream SDK sync record

This is maintenance evidence for the skill. At runtime, the installed SDK is
authoritative; a version match is not required. The machine-readable companion
is [compatibility.json](../compatibility.json).

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

## What changed in agent decisions

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

## Next sync

Compare the SDK implementation and public docs since the reviewed commit;
verify the exact new HEAD and any local SDK modifications. Update only affected
guidance and examples, then run `scripts/validate_skill.py` in the default
interpreter and a documented SDK development interpreter. Update
`compatibility.json` with the reviewed SDK commit and the actual validation
result. A validation skip is not an API pass.

## Validator coverage audit

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
