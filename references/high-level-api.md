# Phase 5 intent API and targeted inspection

Use this page when the task is a common solid operation or a routine check. The
installed SDK is authoritative for signatures. These calls compose the Level 2
public API and never rebuild or save implicitly.

## Preferred and fallback routes

| Intent | Preferred Level 3 | Supported Level 2 fallback |
|---|---|---|
| Create a solid feature | `body.features.pad/pocket/hole/fillet/chamfer/circular_pattern(...)` | `with part.work_in(body): part.part_design.create_*(...)` |
| Draw a common profile | `sketch.rectangle(...)`, `centered_rectangle(...)`, `circle(...)` | One `with sketch.edit() as editor:` group of primitives and constraints |
| Find a top face | `part.geometry.top_face()` | `part.topology.faces(body=body).query().planar().normal_parallel((0, 0, 1)).extreme((0, 0, 1)).one()` |
| Find a specific edge | `part.geometry.find_edge(...)` | One `part.topology.edges(body=body)` snapshot and a composed `.query()` |
| Routine check | `part.inspect.facts(...)` | Specific Level 2 getters or `part.measurement.measure()` when its full result is needed |
| Edit a verified dimension | `pad.length = ...`, `fillet.radius = ...` | The same wrapper's explicit `set_*` method for units or advanced arguments |

Fallback is useful for uncommon intent, composition beyond a helper, debugging,
and public capabilities without a Level 3 abstraction. Level 2 remains supported.
`body.features` is a tuple of `FeatureInfo` values with intent methods attached;
it is not a separate collection to mutate by index.

## Feature calls

```python
from auto_3dx import Catia

part = Catia.attach().part_named("MY_PART")
body = part.bodies.main
sketch = part.sketches.create("BASE_PROFILE", support="XY")
sketch.rectangle(width=50.0, height=30.0, origin=(0.0, 0.0), constraints="dimensioned")
base = body.features.pad("BASE", profile=sketch, length=20.0, direction="+Z")
part.update()
facts = part.inspect.facts("volume", "up_to_date")
```

`body.features.pocket(name, profile, depth, direction="into_material")` cuts from
a face-supported sketch into the solid. `body.features.hole(name, support=face,
center=(x, y), diameter=d, depth=depth)` makes a blind hole; use
`limit="through_all"` and omit `depth` for a through hole. Hole defaults are
written explicitly by the intent helper because CATIA carries them between holes.
Only `direction="into_material"` is supported for Hole. `bottom="flat"` and
`bottom="v"` are verified. Hole reversal, threads, and counterbores are not.

`body.features.fillet(name, edges=[edge], radius=r)` supports exactly one edge.
`body.features.chamfer(name, edge=edge, length=l, angle=45)` uses the verified
length/angle mode. `body.features.circular_pattern(name, feature=seed,
instances=n, total_angle_deg=360, axis="Z")` uses spacing, not CATIA's
unsupported complete-crown mode. Alternatively pass `spacing_deg`, exactly one
of the two. Verified axes are `"X"`, `"Y"`, `"Z"`, a cylindrical `Face`, or a
linear `Edge`; `reverse` flips rotation, with sense documented only for Z.

Pad and Pocket `direction` can be `"along_normal"`, `"against_normal"`, a world
axis such as `"+Z"`, or `"into_material"`/`"out_of_material"` for a sketch the
SDK created on a face. Omitted direction preserves CATIA's defaults. A Pocket
can rebuild yet cut no material, so verify its effect.

## Sketches and properties

`sketch.rectangle(width=..., height=..., origin=(u, v),
constraints="none"|"orientation"|"dimensioned")` and
`sketch.centered_rectangle(width=..., height=..., center=(u, v), ...)` each use
one edit session. `sketch.circle(center=(u, v), radius=...)` is also available.
The rectangle options create 0, 4, or 6 constraints respectively. None proves
full constraint because corner coincidence is not added. For a sketch on a
planar face, use `sketch.frame().to_local((x, y, z))` to place geometry; read
`sketch.geometry()` only after the edition closes.

Preferred in-place edits include `pad.length`, `pocket.depth`, `fillet.radius`,
`chamfer.length1`/`angle`, `hole.diameter`/`depth`, `plane.offset`/`angle`, and
`pattern.instances`/`spacing_deg`. Assignment validates and advances the model
generation but never calls `part.update()`; rebuild and verify afterward.
When changing a through Hole back to blind, supply a fresh depth via
`hole.set_limit("blind", depth=...)`: CATIA rewrites depth on through-all.

## Inspection cost

```python
facts = part.inspect.facts("volume", "up_to_date", "feature_count")
print(facts["volume"], facts["up_to_date"], facts["feature_count"])
print(facts.unavailable)
```

Supported facts: `name`, `up_to_date`, `volume`, `surface_area`, `mass`,
`center_of_gravity`, `feature_count`, `sketch_count`, `body_count`. The four mass
facts share one inertia measurement. `facts()` does no topology search. An empty
or unrebuilt body can make mass facts unavailable, recorded in
`facts.unavailable`; other errors propagate. Use `summary()` or topology only
for a question that needs their breadth. In the Phase 5 live test, targeted
facts were substantially cheaper than `summary()`; exact timing is installation
specific and recorded in the SDK Phase 5 design document.
