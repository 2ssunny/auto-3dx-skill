# auto-3dx capability state

What an agent may rely on today, through SDK v1.0.0 (functional
completeness). Detailed signatures live in the installed package
(`help(auto_3dx.geometry.part_design.PartDesign)` and similar), not here. When
the installed package disagrees with this page, trust the package and report
the drift.

Upstream state reviewed: see `upstream-sync.md`. Live evidence comes from one
installation (`B428_Cloud`); other 3DEXPERIENCE releases are unverified.

The intent layer is described in [high-level-api.md](high-level-api.md). The
table below also records the composable Level 2 fallback. Earlier Phase 4 test
counts in the environment table are historical evidence, not current totals.

## How to read the labels

| Label | Meaning |
|---|---|
| **Verified** | Backed by a live probe and a live integration test: the call succeeded, the rebuild succeeded, and the result was checked. |
| **Partial** | Supported within stated limits only. The limits are part of the capability — do not round them up to "yes". |
| **Not supported** | Absent from the public API. Do not assume it, and do not recreate it with raw COM in a user's project. |

## Python environment

auto-3dx is an ordinary Windows package installed with pip. Its only runtime
dependency is `pywin32`; `com3dx` comes from the 3DEXPERIENCE installation and is
found at runtime. No Python distribution is privileged. Upstream evidence, all
64-bit, live runs on `B428_Cloud`:

| Environment | Python | pywin32 | Unit suite | Live integration |
|---|---|---|---|---|
| Standard CPython venv (python.org), editable install | 3.14.2 | 312 | 1156 passed | **Verified**: 62 passed, 6 skipped |
| Standard CPython venv, regular install | 3.14.2 | 312 | passed at an earlier commit | not run |
| Conda environment (Anaconda), editable install | 3.11.16 | 312 | passed at an earlier commit | 38 passed, 1 skipped, at an earlier commit |
| GitHub Actions Windows runner, regular install | 3.11, 3.12, 3.13, 3.14 | pip-resolved | passed at an earlier commit | none (no 3DEXPERIENCE on the runner) |

- The 6 skips need a Part prepared by hand; they are not failures.
- Phase 1–4 acceptance scripts all pass using the public API only — no raw COM,
  no topology indices, no descriptor parsing.
- Phase 5 SDK documentation reports 11/11 staged live tests and a full live
  suite of 73 passed, 6 skipped on `B428_Cloud`.
- SDK v1.0.0: 1359 unit tests passed (Conda `auto-3dx`, Python
  3.11.16, rerun for this review). The SDK v1 session reports the v1 live
  acceptance suite at 16/16 (the human edge-click stage run separately with
  `AUTO3DX_HUMAN=1`) and the Phase 5 live regression at 11/11, on a disposable
  Part; see `upstream-sync.md` for the exact commits and how that evidence is
  recorded.
- Live runs use a disposable Part named by `AUTO3DX_LIVE_PART`.
- Pending: live integration on Python 3.12 and 3.13 (unit only), the Phase 2–4
  work on Conda, 32-bit Python, Microsoft Store Python, and 3DEXPERIENCE
  releases other than `B428_Cloud`.

## Capability matrix

| Area | Status | Notes |
|---|---|---|
| Intent API | Verified | `body.features.*`, sketch helpers, `part.geometry.*`, `part.inspect.facts/feature/sketch(...)`, writable properties; thin wrappers over public Level 2 |
| User selection | Verified | `part.selection.items()/one()/one_edge()/one_face()/one_feature()/one_sketch()/edges()/faces()`; selected edges and faces are ordinary current-generation handles. Typed refusals: `SelectionCountError`, `SelectionTypeError`, `SelectionOutsidePartError` (ownership proved by COM identity, never by name). Active Part only |
| Highlighting | Verified | `part.selection.set()/add()/clear()`: UI selection only, model and generation unchanged; every element checked first and the count read back |
| Session / attach | Verified | `Catia.attach()`, `active_part()`, `editors()`, `parts()`, `part_named()`, `active_window_title`. Assembly context refused (`NoActivePartError`) |
| Active-Part guard | Verified | Selection-based work (topology search, `part.selection`, `remove_*`, visibility, constraint removal) refuses a non-active Part with `InactivePartError` |
| Parameters | Verified | list/get/set/remove, typed `create_*`/`ensure_*`, unit catalogue. `EnumParam` **read** only — writing is not supported |
| Parameter dependency safety | Partial | `dependents(name)` and the removal guard (`ParameterInUseError`) cover **formula** inputs. Rules, checks, laws, programs and design tables are not covered; `force=True` overrides |
| Formula | Verified | create/ensure/get/list/remove, `relation_name()`, modify/rename/activate/deactivate, `reading(parameter)`, `Formula.inputs()`, `Formula.reads(parameter)` |
| Sketch | Verified | create on origin/user planes or a planar `Face`; `body.sketches` targets one body. Face sketches expose `frame()` and `created_on_face`; `support()` is `None` for a face sketch |
| Sketch geometry | Partial | `sketch.rectangle/centered_rectangle/circle` use one edition. Rectangle constraints: none (0), orientation (4), dimensioned (6) are four independent lines; `fully` (8) shares corner points and is drivable through `width_constraint`/`height_constraint`. Full constraint is a degree-of-freedom count; CATIA's solver status is not read. Editor primitives, `polygon(corners)` and `distance_to_axis(point, axis)` remain available. Read `sketch.geometry()` only after edition closes |
| SketchElement rediscovery | Partial | `elements()`, `get_element(name)`, `element.geometry()` after edition closes; verified line endpoints, circle/arc centre and radius, point coordinates. Unsupported kinds such as spline have no geometry read-back |
| Constraints | Verified | 10 constraint kinds, inside `edit()` only; list/names/get, `broken_count`, dimensional read/write |
| Constraint deletion | Verified | `sketch.constraints.remove(constraint_or_name)`, edit-state aware, verified after fresh-process rediscovery |
| Planes | Verified | `create_offset`, `create_angle`, list/names/get, `len`/iteration/`in`. A new plane needs a rebuild before it can support a sketch (`SupportNotUpdatedError`) |
| Offset plane from a face | Verified | `part.geometry.offset_plane(name, face=, distance=, side="out_of_material"/"into_material")` or `create_offset(name, face, offset, orientation)`; the face must be planar, current and of this Part. Side verified on top, bottom and +X faces; it does not follow the measured normal sign |
| Plane origin and normal | Partial | `plane.origin`, `plane.normal`; answer only after `part.update()` (before it, `AutomationError`). The normal sign is CATIA's frame, not a material side |
| OffsetPlane editing | Verified | `offset` / `set_offset(offset)`; downstream sketch and features regenerate on `part.update()`; rediscovered in a fresh process |
| AnglePlane editing | Verified | `angle` / `set_angle(angle)`; downstream regeneration on `part.update()` |
| Reference-plane dependency guard | Partial | `planes.dependents(plane)`; `planes.remove(plane)` and `remove_geometrical_set()` refuse with `ReferenceInUseError` while a sketch uses the plane (`force=True` overrides). Detection compares sketch frames, so an identical frame on another plane also counts |
| Bodies | Verified | list/names/get/main/create/`remove(name, delete_contents=False)`, `is_up_to_date`, `update()`, `hide()`/`show()`/`is_visible`, `len`/iteration/`in`. Model-backed rediscovery |
| `work_in(body)` | Verified | Targets sketches, features and topology at one body; restores the previous In-Work Object on every exit; nests |
| `work_at(feature)` | Verified | Sets the history insertion position; CATIA inserts immediately after the chosen feature, moving nothing |
| Pad, Pocket | Verified | create/ensure/get/list/remove; depth (`Pad.height`) read and write |
| Pad direction | Verified | `create_pad(..., direction=None)`, `direction`, `set_direction()`, `reverse_direction()`. `None` keeps CATIA's default (along the sketch normal) |
| Pocket direction | Verified | Same API. `None` keeps CATIA's default, **against** the sketch normal — which can cut into nothing while rebuilding successfully. Specify it and verify by volume |
| Shaft, Groove | Verified | Need a centre line; first/second angle read and write. No direction control |
| Rib, Slot | Verified | Profile plus path sketches. No direction control |
| Mirror | Verified | Origin plane |
| Rectangular Pattern | Partial | `create_rectangular_pattern` and `remove_rectangular_pattern(pattern)`. **No dimensional editing** |
| Circular Pattern | Partial | High-level `body.features.circular_pattern(...)` or Level 2 `create_circular_pattern(...)`; verified axes X/Y/Z, cylindrical Face, linear Edge and `reverse`. Full circle via `full_circle=True`, `pattern.full_circle` and `set_full_circle(instances)`, written as count and spacing. No CATIA complete-crown flag, per-instance activation, or radial control |
| Fillet | Verified | `create_edge_fillet` on a body-scoped `Edge`; `radius` / `set_radius` / `radius_parameter()` |
| Chamfer | Partial | `create_chamfer`; `length1` and `angle` with setters. **Length2 cannot be written** |
| Shell | Verified | `create_shell` on a `Face`; `internal_thickness` and `external_thickness` with setters |
| Thickness | Verified | `create_thickness` on a `Face`; `offset` / `set_offset` |
| Hole | Partial | Positioned `create_hole(origin=, diameter=, limit="blind"|"up_to_next"|"through_all", bottom="flat"|"v", head=)` or `body.features.hole(support=, center=, diameter=, ...)`. Heads: `Counterbore(diameter, depth)`, `Countersink(depth, angle_deg=90)`; `hole_type`, `head`, `set_head()`, `set_limit()`. Limit and type are always written against CATIA's carried defaults. The positioned origin is read back and corrected once, else `HolePlacementMismatchError`. No reversal (probed: removes nothing), threads, other families, or moving an existing hole |
| MultiSectionSolid | Partial | create/get/remove, **sections only**. No guides, closing points, coupling or dimensional editing |
| Boolean Remove / Add / Intersect / Assemble | Verified | `create_boolean_*(name, tool_body)` with the work body as target. **The tool body is consumed permanently** |
| Boolean removal | Verified, destructive | `remove_boolean(name, delete_consumed_body=True)` destroys the consumed body |
| Feature suppression | Verified | `is_active`, `activate()`, `deactivate()` (live on Pad, Pocket, Fillet). Advances the generation; no dependency prediction |
| Topology snapshots | Partial | Part-wide or `body=`-scoped, with the `CrossBodyReferenceError` guard. Edges report `from_sketch` for consumed-sketch profile edges. **No feature-level scoping**, no persistent identity, process-local registry |
| Topology ownership | Partial | `current_owner_feature_name` (alias `owner_feature_name`) is the **current** BRep owner, not provenance. `owner_body_name` falls back to a unique name match and otherwise stays `None` — unknown, not "main body" |
| Face measurement | Partial | `face.geometry`: `surface_type`, `area_mm2`, `center_mm`, `perimeter_mm`; planar `normal` and `plane_origin_mm`; cylindrical `radius_mm`. **Planar and cylindrical only**; others are `"unknown"` |
| Plane normals | Partial | Measured topology normals describe the supporting plane, **not** the outward solid normal. A sketch newly created on a planar face has a separately verified outward frame normal on tested faces |
| Edge measurement | Partial | `edge.geometry`: `curve_type`, `length_mm`, `start_mm`/`mid_mm`/`end_mm`; line `direction`; circle/arc `radius_mm`, `center_mm`, `angle_deg`. **Line, circle and arc only**; others are `"unknown"` |
| Semantic geometry query | Verified | `snapshot.query()` with type, orientation, size, position and current-owner steps and explicit tolerances (`geometry-query.md`) |
| Semantic finders | Verified | `part.geometry.top_face/bottom_face/find_planar_face/find_cylindrical_face/find_edge`; strict one-match result. `part.geometry.edges()` drops sketch profile edges |
| Face-edge adjacency | Verified | `EdgeQuery.adjacent_to(face)`, `FaceQuery.adjacent_to(edge)`, `part.topology`/`part.geometry` `edges_of(face)`/`faces_of(edge)`, `find_edge(adjacent_to=)`. An edge bounds a face when its start, middle and end measure on the bounded face (`Face.distance_to`); profile edges never count |
| Plane coincidence | Partial | `EdgeQuery.on_plane_of(face)` checks coplanarity, **not adjacency**; use `adjacent_to` for bounding edges |
| Element descriptions | Verified | `face.describe()`, `edge.describe()`: one line of measured facts and current owner, no index or BRep name; used in query error messages |
| Query ambiguity handling | Verified | `one()` raises `TopologyQueryNoMatchError` / `TopologyQueryAmbiguousError`; rankings keep ties within tolerance |
| Measurement | Verified | `measure(item)` → `volume_mm3`, `area_mm2`, `mass_kg`, `cog_mm`. Refuses a target that is not rebuilt (`TargetNotUpToDateError`) and never rebuilds |
| Inspection | Verified | `part.inspect.facts(...)` for named, targeted facts without topology enumeration; `inspect.feature(name)` (`FeatureDetails`) and `inspect.sketch(name)` for one object in any body; `summary()` for comprehensive inspection including topology counts |
| Update diagnostics | Partial | `part.inspect.update_issues()` and `PartUpdateError.issues` (`UpdateIssue`: `name`, `kind`, `body_name`, `up_to_date`, `active`). **Affected state only — not root-cause analysis** |
| Deletion | Verified | Per-kind `remove_*`; cascades and guards in `safety.md` §4 |
| Rebuild | Verified | `part.update()`, `part.update(target)`, `body.update()`, `part.is_up_to_date(target=None)`, `body.is_up_to_date` |

## Not supported

If a task needs one of these, **stop and report the SDK gap**. Do not reach for
raw COM, a topology index or descriptor parsing.

- Outward-facing solid normals; vertex selection or vertex handles.
- Cone, sphere, torus, spline and B-surface measurement.
- Persistent topology naming across rebuilds or processes; historical topology
  provenance; full design-intent reconstruction.
- Feature-level topology scoping.
- Root-cause update diagnosis; automatic suppression dependency prediction.
- A general dependency graph (Formula / Rule / Check / Law and beyond).
- Reading CATIA's sketch solver status (full constraint is counted, not read).
- Direction control for Shaft, Groove and Rib.
- CATIA's Circular Pattern complete-crown flag, per-instance activation, and
  advanced radial control.
- Rectangular Pattern dimensional editing.
- Restoring a consumed Boolean tool body; replacing a Boolean operand; body
  duplication or copy workflows.
- Hole reversal, threads, moving an existing hole, and Hole families beyond
  simple, counterbored and countersunk.
- Loft guides, closing points and coupling; broad GSD surface geometry; Split.
- Writing an `EnumParam`; sketch read-back during an active edition.
- Setting the In-Work Object outside `work_in` / `work_at`.
- Renaming or reordering bodies; geometrical sets inside a body; axis systems.
- Product / Assembly editing; PLM object creation.
- `Save`, `SaveAs`, `PLMPropagate`, and export.
- Use from worker threads (main thread only).

## Known limitations of the safety guards

- The cross-body guard allows an operation through when ownership is unknown.
- Body-scoped snapshots include consumed-sketch profile edges. They carry
  `edge.from_sketch is True`; `EdgeQuery.solid()` and `part.geometry.edges()`
  drop them. `from_sketch is None` (owner not decidable) is kept by `solid()`.
- A selection item whose owning body cannot be proved is refused, even when a
  body name matches.
- The generation registry is process-local: a new process must take fresh
  snapshots and re-run its queries.
- The plane guard errs towards refusing when two planes share a frame.
- Update diagnostics show what is affected, never what caused the failure.

## Deprecated — do not use in new code

| Deprecated | Use instead |
|---|---|
| Selecting topology by `index` or by parsing `descriptor` | A semantic query with `one()` (`geometry-query.md`) |
| `owner_feature_name` in new code | `current_owner_feature_name` (same value, honest name) |
| `part.part_design.snapshot_edges()` / `snapshot_faces()` | `part.topology.edges()` / `faces()` |
| Passing raw 2D COM objects to constraints or `set_center_line` | The `SketchElement` the editor returned, or `sketch.get_element(name)` |
| Reading the active window through raw Automation | `catia.active_window_title` |
| Deleting and recreating a feature to change a verified dimension | The feature's own setter (`editing.md`) |
| An offset plane used only to flip a Pad or Pocket | `direction=` / `set_direction()` |
