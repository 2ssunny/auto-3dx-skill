# Intent API and targeted inspection

Use this page when the task is a common solid operation or a routine check. The
installed SDK is authoritative for signatures. These calls compose the Level 2
public API and never rebuild or save implicitly.

## Preferred and fallback routes

| Intent | Preferred Level 3 | Supported Level 2 fallback |
|---|---|---|
| Create a solid feature | `body.features.pad/pocket/hole/fillet/chamfer/circular_pattern(...)` | `with part.work_in(body): part.part_design.create_*(...)` |
| Draw a common profile | `sketch.rectangle(...)`, `centered_rectangle(...)`, `circle(...)` | One `with sketch.edit() as editor:` group; `editor.polygon(corners)` for shared corners |
| Find a top face | `part.geometry.top_face()` | `part.topology.faces(body=body).query().planar().normal_parallel((0, 0, 1)).extreme((0, 0, 1)).one()` |
| Find a specific edge | `part.geometry.find_edge(...)` | One `part.topology.edges(body=body)` snapshot and a composed `.query()` |
| Edges of a face, faces of an edge | `part.geometry.edges_of(face)`, `faces_of(edge)`, `find_edge(adjacent_to=face, ...)` | `EdgeQuery.adjacent_to(face)`, `FaceQuery.adjacent_to(edge)` |
| The element the user picked | `part.selection.one_edge()` / `one_face()` / `one_feature()` / `one_sketch()` | `part.selection.items()` and each `SelectedItem.kind` |
| Plane parallel to a face | `part.geometry.offset_plane(name, face=face, distance=d, side=...)` | `part.planes.create_offset(name, face, offset, orientation)` |
| Routine check | `part.inspect.facts(...)` | Specific Level 2 getters or `part.measurement.measure()` when its full result is needed |
| One named feature or sketch | `part.inspect.feature(name)`, `part.inspect.sketch(name)` | `part.part_design.get_*(name)` getters, `part.sketches.get(name).geometry()` |
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
center=(x, y), diameter=d, depth=depth)` makes a blind hole. `limit="up_to_next"`
stops at the next face the hole meets and `limit="through_all"` goes through;
both take no `depth`. `head=Counterbore(diameter, depth)` or
`head=Countersink(depth, angle_deg=90)` (from `auto_3dx.geometry`) adds a head;
`None` is a simple hole. Limit, type, bottom and diameter are written explicitly
because CATIA carries them between holes. Only `direction="into_material"` is
offered: a reversed hole was probed and removed nothing. `bottom="flat"` and
`bottom="v"` are verified. Threads and other hole families are not supported.

The positioned hole's origin is read back before `hole()` returns. CATIA can snap
an off-centre hole on a face bounded by one circle to that circle's centre; the
SDK moves it once and raises `HolePlacementMismatchError` (with `requested`,
`actual` and `hole_name`) if it is still wrong. The hole then exists under its
name: remove it before continuing.

`body.features.fillet(name, edges=[edge], radius=r)` supports exactly one edge.
`body.features.chamfer(name, edge=edge, length=l, angle=45)` uses the verified
length/angle mode. `body.features.circular_pattern(name, feature=seed,
instances=n, full_circle=True, axis="Z")` spreads `n` copies over 360 degrees.
Alternatively pass `total_angle_deg` or `spacing_deg`: exactly one of the three.
The SDK always writes count and spacing; CATIA's own complete-crown flag was
accepted and ignored live, so it is not used. Verified axes are `"X"`, `"Y"`,
`"Z"`, a cylindrical `Face`, or a linear `Edge`; `reverse` flips rotation, with
sense documented only for Z. `pattern.full_circle` reads whether count times
spacing is 360; `pattern.set_full_circle(instances)` changes the count and keeps
it a full circle, where assigning `instances` alone keeps the old spacing.

Pad and Pocket `direction` can be `"along_normal"`, `"against_normal"`, a world
axis such as `"+Z"`, or `"into_material"`/`"out_of_material"` for a sketch the
SDK created on a face. Omitted direction preserves CATIA's defaults. A Pocket
can rebuild yet cut no material, so verify its effect.

## Sketches and properties

`sketch.rectangle(width=..., height=..., origin=(u, v),
constraints="none"|"orientation"|"dimensioned"|"fully")` and
`sketch.centered_rectangle(width=..., height=..., center=(u, v), ...)` each use
one edit session. `sketch.circle(center=(u, v), radius=...)` is also available.
`none`, `orientation` and `dimensioned` draw four independent lines with 0, 4 or
6 constraints; constraining one side moves only that side. `fully` draws shared
corner points (`profile.corners`) with eight constraints: horizontal and vertical
sides, width, height, and the lower-left corner's distances to the sketch axes.
Drive it later with `profile.width_constraint.set_value(70.0)` or
`height_constraint`, then `part.update()`. For `centered_rectangle(...,
constraints="fully")` the lower-left corner is the anchor, so a wider rectangle
grows to the right, not about its centre. The count of eight is a degree-of-freedom
count; CATIA's solver status is not read.

For a sketch on a planar face, use `sketch.frame().to_local((x, y, z))` to place
geometry; read `sketch.geometry()` only after the edition closes.

`part.geometry.offset_plane(name, face=top, distance=10.0,
side="out_of_material")` creates a plane parallel to a planar face on a material
side (`"into_material"` is the other choice). The side does not follow the
measured face normal, which reads +Z for both top and bottom faces. Call
`part.update()` before sketching on the plane; `plane.origin` and `plane.normal`
answer only after that rebuild and confirm where it went.

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

```python
details = part.inspect.feature("BOLT_HOLE")
print(details.kind, details.body_name, details.up_to_date, details.active)
print(details.parameters["diameter"], details.parameters["head"])
profile = part.inspect.sketch("BASE_PROFILE")
print(len(profile.lines))
```

`inspect.feature(name, body=None)` finds one feature by name in any body and
returns `FeatureDetails`: `name`, `kind`, `body_name`, `up_to_date`, `active`
(`None` when CATIA reports no activity), and `parameters`, the verified
dimensions of wrapped kinds (a hole reports `diameter`, `depth`, `limit`,
`bottom`, `hole_type`, `head`, `origin`, `direction`). An unwrapped kind is
still reported, with empty `parameters`. `inspect.sketch(name, body=None)`
returns the same `SketchGeometry` as `sketch.geometry()` from any body. A
duplicate name raises `AmbiguousNameError`; pass `body=`. Both are read-only.

`part.bodies` and `part.planes` support `len()`, iteration and `name in ...`,
read from the live Part like the other collections.

## User selection and highlighting

```python
edge = part.selection.one_edge()        # the one edge the user clicked
print(edge.describe())                  # measured facts; no index or BRep name
part.selection.set(edge)                # highlight it; only the UI selection changes
part.selection.clear()
```

`part.selection` reads the CATIA selection into SDK wrappers: `items()` returns
`SelectedItem` records (`position`, `kind`, `type_name`, `name`, `element`);
`one()`, `one_edge()`, `one_face()`, `one_feature()`, `one_sketch()` need exactly
one item of that kind; `edges()` and `faces()` need every item to be that kind.
A selected edge or face is a normal `Edge`/`Face` stamped with the current
generation, usable by any feature and stale after the next mutation. An item is
accepted only when one of this Part's bodies provably holds it
(`SelectionOutsidePartError` otherwise). Wrong counts raise
`SelectionCountError`, wrong kinds `SelectionTypeError`. Reading never changes
the model or the selection.

`set(*elements)` and `add(*elements)` highlight edges, faces, features, sketches
or bodies, check every element before touching the selection, and verify the
count afterwards; `clear()` deselects. They change only the UI selection and do
not advance the generation. Both directions require the active Part.
