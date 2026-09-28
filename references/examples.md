# Engineering workflows with the public Phase 5 API

These are independent patterns for an already open Part. Replace `MY_PART` and
feature names with the user's actual target and noncolliding names. Each edit
remains unsaved. The high-level call shapes follow the SDK's
`examples/intent_api.py`; the fallback follows its public query implementation.
Use a fresh topology result after a geometry-changing update.

## Simple block

```python
from auto_3dx import Catia

part = Catia.attach().part_named("MY_PART")
body = part.bodies.main
before = part.inspect.facts("up_to_date", "feature_count")
sketch = part.sketches.create("BLOCK_PROFILE", support="XY")
sketch.centered_rectangle(width=50.0, height=30.0, constraints="dimensioned")
profile = sketch.geometry()  # the helper closed its edit session
base = body.features.pad("BLOCK", profile=sketch, length=20.0, direction="+Z")
part.update()
after = part.inspect.facts("volume", "up_to_date")
print(before["up_to_date"], len(profile.lines), after["volume"])
```

`dimensioned` adds horizontal/vertical and length constraints, but the rectangle
is not fully constrained: it has no corner coincidence constraints.

## Secondary sketch on the top face and Pocket

```python
from auto_3dx import Catia

part = Catia.attach().part_named("MY_PART")
body = part.bodies.main
top = part.geometry.top_face()
cut = part.sketches.create("TOP_CUT_PROFILE", support=top)
local_corner = cut.frame().to_local((10.0, 5.0, top.geometry.center_mm[2]))
cut.rectangle(width=8.0, height=6.0, origin=local_corner)
cut.geometry()  # read back only after the helper's edition closed
before = part.inspect.facts("volume")
body.features.pocket("TOP_CUT", profile=cut, depth=3.0, direction="into_material")
part.update()
after = part.inspect.facts("volume", "up_to_date")
print(before["volume"] - after["volume"], after["up_to_date"])
```

The example assumes a horizontal top face and a local profile point that lies
inside it. Check those geometric assumptions for the actual Part.

## Positioned through Hole and a circular pattern

```python
from auto_3dx import Catia

part = Catia.attach().part_named("MY_PART")
body = part.bodies.main
top = part.geometry.top_face()
hole = body.features.hole(
    "BOLT_HOLE", support=top, center=(15.0, 0.0), diameter=4.0,
    limit="through_all", bottom="flat",
)
body.features.circular_pattern(
    "BOLT_CIRCLE", feature=hole, instances=6, total_angle_deg=360.0, axis="Z",
)
part.update()
print(part.inspect.facts("volume", "up_to_date")["up_to_date"])
```

For a blind Hole use `depth=...` with `limit="blind"`. `center` may also be a
global `(x, y, z)` point on the face. A two-value centre is supported for a
face normal parallel to a world axis. Rebuild before finding fresh topology.

## Semantic Fillet or Chamfer

```python
from auto_3dx import Catia

part = Catia.attach().part_named("MY_PART")
body = part.bodies.main
edge = part.geometry.find_edge(kind="line", parallel="Z", nearest=(25.0, 15.0, 10.0))
fillet = body.features.fillet("ROUND_CORNER", edges=[edge], radius=2.0)
part.update()
print(fillet.radius, part.inspect.facts("up_to_date")["up_to_date"])
```

For a bevel, use `body.features.chamfer("BEVEL", edge=edge, length=1.5)`
instead. The finder requires exactly one match; refine intent if it is
ambiguous. A fillet call supports one edge.

## Property and parameter revision

```python
from auto_3dx import Catia

part = Catia.attach().part_named("MY_PART")
pad = part.part_design.get_pad("BLOCK")
old_length = pad.length
pad.length = 24.0
part.parameters.set("WIDTH", 55.0, unit="mm")
part.update()
print(old_length, pad.length, part.inspect.facts("volume")["volume"])
```

Read the previous valid values before a risky revision so a failed update can
be repaired by restoring them and rebuilding. Assignments and `set()` do not
rebuild. The named parameter must already exist in the target Part.

## Low-level query fallback

Use a composed query when the intent is more specific than a semantic finder.
This is still public API. The query uses a single body-scoped snapshot and
requires one match.

```python
from auto_3dx import Catia

part = Catia.attach().part_named("MY_PART")
body = part.bodies.main
snapshot = part.topology.faces(body=body)
top = snapshot.query().planar().normal_parallel((0, 0, 1)).extreme((0, 0, 1)).one()
print(top.geometry.area_mm2)
```

For a circular rim with radius 4 mm in that plane, continue with an **edge**
snapshot:

```python
edges = part.topology.edges(body=body)
rim = edges.query().circular().on_plane_of(top).radius_near(4.0).nearest(
    (15.0, 0.0, top.geometry.center_mm[2])
).one()
print(rim.geometry.length_mm)
```

`on_plane_of(top)` asserts plane coincidence only, not adjacency. After any
geometry-changing edit, take a new snapshot before selecting again.

## Advanced Level 2 workflows

These public API examples preserve coverage for operations whose engineering
intent needs more context than a Level 3 helper. Use them only for the relevant
task, and select names and geometry from the actual Part.

### Detailed diagnosis and model-backed parameters

```python
from auto_3dx import Catia

catia = Catia.attach()
print(catia.active_window_title)
part = catia.part_named("MY_PART")
summary = part.inspect.summary()  # full inspection for diagnosis, not a routine poll
print(summary.render(), summary.in_work_object)
print(part.parameters.user_names(), part.formulas.names())
width = part.parameters.get("WIDTH")
print(width.short_name, width.kind, width.value, width.unit)
print(part.parameters.dependents("WIDTH"))
```

Check formula dependents before changing or removing a parameter. Removal of a
pre-existing object requires the user's specific intent.

### Low-level Pocket with measured effect

```python
from auto_3dx import Catia
from auto_3dx.geometry.part_design import DIRECTION_ALONG_SKETCH_NORMAL

part = Catia.attach().part_named("MY_PART")
body = part.bodies.main
before = part.measurement.measure().volume_mm3
sketch = part.sketches.create("CUT_PROFILE", support="XY")
with sketch.edit() as editor:
    editor.circle(0.0, 0.0, 4.0)
with part.work_in(body):
    pocket = part.part_design.create_pocket(
        "LOW_LEVEL_CUT", sketch, 10.0, direction=DIRECTION_ALONG_SKETCH_NORMAL
    )
part.update()
removed = before - part.measurement.measure().volume_mm3
print(pocket.direction, removed)
```

This direction suits a solid above XY. Verify that `removed` is positive for
the actual model; successful update alone is insufficient.

### Roll back a failed dimension edit

```python
from auto_3dx import Catia, PartUpdateError

part = Catia.attach().part_named("MY_PART")
pad = part.part_design.get_pad("BASE")
previous = pad.length
pad.length = 1.0
try:
    part.update()
except PartUpdateError as error:
    for issue in error.issues:
        print(issue.name, issue.kind, issue.body_name, issue.up_to_date, issue.active)
    pad.length = previous
    part.update()
    print(part.is_up_to_date())
    raise
```

The issues describe affected features, not necessarily the cause. Restore the
last valid value before considering removal.

### Plane edit, sketch rediscovery, and history position

```python
from auto_3dx import Catia

part = Catia.attach().part_named("MY_PART")
plane = part.planes.get("BOSS_PLANE")
previous_offset = plane.offset
plane.offset = 8.0
part.update()
print(previous_offset, part.planes.dependents(plane))

sketch = part.sketches.get("RIB_PROFILE")
print(sketch.element_names())
line = sketch.get_element("Line.1")
print(line.geometry())  # read only after the sketch edition is closed
with part.work_at(part.part_design.get_pad("BASE")):
    part.part_design.create_pad("RIB", sketch, 6.0)
part.update()
```

This assumes `BOSS_PLANE` is an offset plane and the named sketch and base Pad
already exist. `work_at` chooses insertion position and restores prior context.

### Another body and a consuming boolean

```python
from auto_3dx import Catia

part = Catia.attach().part_named("MY_PART")
tool = part.bodies.create("TOOL_BODY")
with part.work_in(tool):
    sketch = part.sketches.create("TOOL_PROFILE", support="XY")
    with sketch.edit() as editor:
        editor.rectangle(40.0, 30.0)
    part.part_design.create_pad("TOOL_PAD", sketch, 20.0)
tool.update()
print(part.measurement.measure(tool).volume_mm3)

housing = part.bodies.get("HOUSING")
with part.work_in(housing):
    cut = part.part_design.create_boolean_remove("CUT_TOOL", tool)
part.update()
print(cut.operation, cut.tool_body_name, part.bodies.names())
```

The boolean consumes `TOOL_BODY` permanently. Use this pattern only when the
user intends that consumption and the tool geometry intersects the housing.

### Pattern revision and reversible suppression

```python
from auto_3dx import Catia, PartUpdateError

part = Catia.attach().part_named("MY_PART")
seed = part.part_design.get_pocket("BOLT_HOLE")
pattern = part.part_design.create_circular_pattern(
    "BOLT_CIRCLE", seed, 6, 60.0, axis="Z"
)
part.update()
pattern.instances = 8
part.update()
print(pattern.instances, pattern.spacing_deg)

fillet = part.part_design.get_edge_fillet("EDGE_ROUND")
fillet.deactivate()
try:
    part.update()
except PartUpdateError:
    fillet.activate()
    part.update()
    raise
```

Suppression changes the model generation. A topology handle from before it
must be reselected. Restore the prior active state if the rebuild fails.
