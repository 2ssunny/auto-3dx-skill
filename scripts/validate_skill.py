"""Validates the auto-3dx skill against its document contract and the installed SDK.

Two checks run:

1. Document contract (standard library only): frontmatter, short entrypoint,
   links, compatibility metadata, core rules, paths, and retired-location checks.
2. API check (needs `auto_3dx` importable): Phase 5 and SDK v1 public symbols and every
   ```python block in the code-bearing references. It checks syntax, inferred
   members, call signatures, package-root exports, retired names, and raw COM
   or private SDK names. Without `auto_3dx`, the API check is SKIPPED, not a pass.

Run it with the interpreter whose auto-3dx installation should be checked -- a venv,
a Conda environment, or any other Python. It never looks for another interpreter,
and it prints which interpreter and which `auto_3dx` it used:

    python scripts/validate_skill.py

`--require-sdk` makes a SKIPPED API check a failure; CI uses it so a run without the
SDK can never pass:

    python scripts/validate_skill.py --require-sdk

It finds the skill from its own location (the repository root is the parent of
`scripts/`), so it runs from any working directory and does not depend on what
the checkout folder is called.
"""

import argparse
import ast
import collections.abc
import dataclasses
import importlib
import importlib.util
import inspect
import json
import re
import sys
import types
import typing
from pathlib import Path
from typing import Any

SKILL_DIR = Path(__file__).resolve().parent.parent
CODE_FILES = (
    "SKILL.md",
    "references/high-level-api.md",
    "references/examples.md",
    "references/topology.md",
    "references/editing.md",
    "references/part-design.md",
    "references/geometry-query.md",
)
ALLOWED_FRONTMATTER_KEYS = {"name", "description"}
#: Agents expose the skill under this name, whatever the checkout folder is called.
SKILL_NAME = "auto-3dx"
#: The skill's former home inside 2ssunny/ai-agents; this repository replaced it.
RETIRED_LOCATION = "skills/global/auto-3dx"
TEXT_SUFFIXES = {".md", ".yaml", ".py"}
COMPATIBILITY_FILE = "compatibility.json"
PHASE5_PUBLIC_SYMBOLS = (
    "auto_3dx.highlevel.features.BodyFeatures.pad",
    "auto_3dx.highlevel.features.BodyFeatures.pocket",
    "auto_3dx.highlevel.features.BodyFeatures.hole",
    "auto_3dx.highlevel.features.BodyFeatures.fillet",
    "auto_3dx.highlevel.features.BodyFeatures.chamfer",
    "auto_3dx.highlevel.features.BodyFeatures.circular_pattern",
    "auto_3dx.geometry.sketch.Sketch.rectangle",
    "auto_3dx.geometry.sketch.Sketch.centered_rectangle",
    "auto_3dx.geometry.sketch.Sketch.circle",
    "auto_3dx.geometry.sketch.Sketch.geometry",
    "auto_3dx.geometry.sketch.Sketch.frame",
    "auto_3dx.geometry.sketch.SketchElement.geometry",
    "auto_3dx.highlevel.finders.PartGeometry.top_face",
    "auto_3dx.highlevel.finders.PartGeometry.find_edge",
    "auto_3dx.inspect.summary.Inspector.facts",
    "auto_3dx.geometry.query.EdgeQuery.on_plane_of",
    "auto_3dx.geometry.part_design.Pad.length",
    "auto_3dx.geometry.part_design.Pocket.depth",
    "auto_3dx.geometry.part_design.ConstRadEdgeFillet.radius",
    "auto_3dx.geometry.part_design.Hole.diameter",
    "auto_3dx.geometry.part_design.Hole.depth",
    "auto_3dx.geometry.part_design.Hole.set_limit",
    "auto_3dx.geometry.part_design.CircularPattern.instances",
    "auto_3dx.geometry.part_design.CircularPattern.spacing_deg",
    "auto_3dx.geometry.planes.OffsetPlane.offset",
    "auto_3dx.geometry.part_design.PartDesign.create_circular_pattern",
)
SDK_V1_PUBLIC_SYMBOLS = (
    "auto_3dx.core.part.Part.selection",
    "auto_3dx.geometry.selection.PartSelection.items",
    "auto_3dx.geometry.selection.PartSelection.one",
    "auto_3dx.geometry.selection.PartSelection.one_edge",
    "auto_3dx.geometry.selection.PartSelection.one_face",
    "auto_3dx.geometry.selection.PartSelection.one_feature",
    "auto_3dx.geometry.selection.PartSelection.one_sketch",
    "auto_3dx.geometry.selection.PartSelection.edges",
    "auto_3dx.geometry.selection.PartSelection.faces",
    "auto_3dx.geometry.selection.PartSelection.set",
    "auto_3dx.geometry.selection.PartSelection.add",
    "auto_3dx.geometry.selection.PartSelection.clear",
    "auto_3dx.inspect.summary.Inspector.feature",
    "auto_3dx.inspect.summary.Inspector.sketch",
    "auto_3dx.geometry.faces.Face.describe",
    "auto_3dx.geometry.faces.Face.distance_to",
    "auto_3dx.geometry.edges.Edge.describe",
    "auto_3dx.geometry.edges.Edge.from_sketch",
    "auto_3dx.geometry.query.EdgeQuery.adjacent_to",
    "auto_3dx.geometry.query.EdgeQuery.solid",
    "auto_3dx.geometry.query.FaceQuery.adjacent_to",
    "auto_3dx.geometry.topology.Topology.edges_of",
    "auto_3dx.geometry.topology.Topology.faces_of",
    "auto_3dx.highlevel.finders.PartGeometry.edges_of",
    "auto_3dx.highlevel.finders.PartGeometry.faces_of",
    "auto_3dx.highlevel.finders.PartGeometry.offset_plane",
    "auto_3dx.geometry.planes.Plane.origin",
    "auto_3dx.geometry.planes.Plane.normal",
    "auto_3dx.geometry.part_design.Hole.hole_type",
    "auto_3dx.geometry.part_design.Hole.head",
    "auto_3dx.geometry.part_design.Hole.set_head",
    "auto_3dx.geometry.part_design.CircularPattern.full_circle",
    "auto_3dx.geometry.part_design.CircularPattern.set_full_circle",
    "auto_3dx.geometry.sketch.SketchEditor.polygon",
    "auto_3dx.geometry.sketch.SketchEditor.distance_to_axis",
    "auto_3dx.highlevel.profiles.RectangleProfile.width_constraint",
    "auto_3dx.highlevel.profiles.RectangleProfile.height_constraint",
)
SETTABLE_SYMBOLS = {
    "Pad.length", "Pocket.depth", "ConstRadEdgeFillet.radius", "Hole.diameter",
    "Hole.depth", "CircularPattern.instances", "CircularPattern.spacing_deg",
    "OffsetPlane.offset",
}
FORBIDDEN_EXAMPLE_NAMES = {
    "win32com", "com3dx", "com_object", "ShapeFactory", "HybridShapeFactory",
    "Selection", "_com", "_generation",
}
MARKDOWN_LINK = re.compile(r"\]\(([^)\s]+)\)")
MAX_SKILL_LINES = 200
USER_PATH_PATTERNS = (r"[A-Za-z]:\\Users\\", r"/home/[a-z]+/", r"/Users/[a-z]+/")

#: Retired or deprecated upstream names that examples must not teach.
RETIRED_NAMES = {
    "snapshot_edges": "use part.topology.edges()",
    "snapshot_faces": "use part.topology.faces()",
    "editor_com_object": "use public measurement and inspection APIs",
    "raw": "use public SDK APIs",
}

CODE_BLOCK = re.compile(r"^```python\n(.*?)^```", re.DOTALL | re.MULTILINE)
FRONTMATTER = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)
SEQUENCE_ORIGINS = (
    list,
    tuple,
    collections.abc.Iterator,
    collections.abc.Iterable,
    collections.abc.Sequence,
    collections.abc.Generator,
)
MISSING = object()

# Inferred types are small tuples:
#   ("inst", cls)  an instance of an auto_3dx class
#   ("cls", cls)   the class object itself
#   ("mod", mod)   an auto_3dx module
#   ("seq", item)  a list, tuple or iterator whose items have type `item`
#   ("method", cls, name, static_member, owner_kind)
Inferred = tuple | None


def read_text(path: Path) -> str:
    """Reads a file as UTF-8 with normalised newlines."""
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def check_document() -> list[str]:
    """Checks the SKILL.md contract shared by every skill in this repository.

    Returns:
        One message per failure; empty when the contract holds.
    """
    failures: list[str] = []
    skill_text = read_text(SKILL_DIR / "SKILL.md")
    match = FRONTMATTER.match(skill_text)
    if match is None:
        return ["SKILL.md must open with a --- frontmatter block."]
    keys = re.findall(r"^([A-Za-z_][\w-]*):", match.group(1), re.MULTILINE)
    extra = set(keys) - ALLOWED_FRONTMATTER_KEYS
    if extra:
        failures.append(f"Frontmatter has platform-specific keys: {sorted(extra)}.")
    name = re.search(r"^name:\s*(\S+)\s*$", match.group(1), re.MULTILINE)
    if name is None or name.group(1) != SKILL_NAME:
        failures.append(f"Frontmatter name must be {SKILL_NAME!r}.")
    if not re.search(r"^description:\s*\S", match.group(1), re.MULTILINE):
        failures.append("Frontmatter description must not be empty.")
    lines = len(skill_text.splitlines())
    if lines > MAX_SKILL_LINES:
        failures.append(f"SKILL.md is {lines} lines; move detail into references/.")
    if "Prefer the highest-level public auto-3dx API" not in skill_text:
        failures.append("SKILL.md must state the high-level-first operating rule.")
    if "part.update()" not in skill_text or "part.inspect.facts" not in skill_text:
        failures.append("SKILL.md must explain explicit updates and targeted inspection.")
    failures.extend(check_compatibility())
    for link in sorted(set(re.findall(r"\]\((references/[\w./-]+)\)", skill_text))):
        if not (SKILL_DIR / link).is_file():
            failures.append(f"SKILL.md links {link}, which does not exist.")
    for path in skill_files():
        relative = path.relative_to(SKILL_DIR).as_posix()
        text = read_text(path)
        if path.suffix == ".md":
            failures.extend(check_links(path, relative, text))
        if path.resolve() == Path(__file__).resolve():
            continue
        for pattern in USER_PATH_PATTERNS:
            if re.search(pattern, text):
                failures.append(f"{relative} contains a user path.")
        if RETIRED_LOCATION in text:
            failures.append(f"{relative} refers to the retired location {RETIRED_LOCATION}.")
    return failures


def check_compatibility() -> list[str]:
    """Checks the traceable Skill-to-SDK compatibility record."""
    path = SKILL_DIR / COMPATIBILITY_FILE
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        return [f"{COMPATIBILITY_FILE} cannot be read: {error}"]
    if not isinstance(record, dict):
        return [f"{COMPATIBILITY_FILE} must contain a JSON object."]
    required = {"skill_version", "sdk_commit", "sdk_package_version", "public_api_expectation"}
    missing = required - record.keys()
    failures = [f"{COMPATIBILITY_FILE} is missing {sorted(missing)}"] if missing else []
    if not re.fullmatch(r"[0-9a-f]{40}", str(record.get("sdk_commit", ""))):
        failures.append(f"{COMPATIBILITY_FILE} sdk_commit must be a full SHA-1 commit ID.")
    for field in required - {"sdk_commit"}:
        if not isinstance(record.get(field), str) or not record[field].strip():
            failures.append(f"{COMPATIBILITY_FILE} {field} must be nonempty text.")
    return failures


def skill_files() -> list[Path]:
    """Lists the repository's text files, skipping hidden directories such as .git."""
    files = []
    for path in sorted(SKILL_DIR.rglob("*")):
        if any(part.startswith(".") for part in path.relative_to(SKILL_DIR).parts):
            continue
        if path.is_file() and path.suffix in TEXT_SUFFIXES:
            files.append(path)
    return files


def check_links(path: Path, relative: str, text: str) -> list[str]:
    """Checks that each relative Markdown link resolves to a file inside the repository."""
    failures = []
    root = SKILL_DIR.resolve()
    for target in sorted(set(MARKDOWN_LINK.findall(text))):
        if re.match(r"[A-Za-z][\w+.-]*:", target) or target.startswith("#"):
            continue  # URLs, mailto: and in-page anchors
        resolved = (path.parent / target.split("#", 1)[0]).resolve()
        if not resolved.is_relative_to(root):
            failures.append(f"{relative} links {target}, which is outside the repository.")
        elif not resolved.exists():
            failures.append(f"{relative} links {target}, which does not exist.")
    return failures


def resolve_hint(hint: Any) -> Inferred:
    """Turns a type hint into an inferred type, or None when it is not useful."""
    origin = typing.get_origin(hint)
    if origin in (typing.Union, types.UnionType):
        options = [arg for arg in typing.get_args(hint) if arg is not type(None)]
        return resolve_hint(options[0]) if len(options) == 1 else None
    if origin in SEQUENCE_ORIGINS:
        args = [arg for arg in typing.get_args(hint) if arg is not Ellipsis]
        return ("seq", resolve_hint(args[0]) if args else None)
    if inspect.isclass(hint) and hint.__module__.startswith("auto_3dx"):
        return ("inst", hint)
    return None


def _auto_3dx_classes() -> "dict[str, type]":
    """Every public class defined in a loaded auto_3dx module, by name.

    A name defined by two modules is left out rather than guessed.
    """
    found: dict[str, type] = {}
    clashes: set[str] = set()
    for module_name, module in list(sys.modules.items()):
        if module is None or not module_name.startswith("auto_3dx"):
            continue
        for name, value in vars(module).items():
            if name.startswith("_") or not inspect.isclass(value):
                continue
            if value.__module__ != module_name:
                continue
            if name in found and found[name] is not value:
                clashes.add(name)
            found[name] = value
    for name in clashes:
        del found[name]
    return found


def return_type(function: Any, owner: type | None = None) -> Inferred:
    """Reads a function's return annotation as an inferred type."""
    function = inspect.unwrap(function)
    try:
        hints = typing.get_type_hints(function)
    except NameError:
        # The SDK imports some return types only under TYPE_CHECKING or inside the
        # method (Snapshot.query(), Inspector.feature(), Sketch.rectangle()), so the
        # forward annotation is not in the module globals. Resolve it against the
        # classes the loaded auto_3dx modules define.
        try:
            hints = typing.get_type_hints(function, localns=_auto_3dx_classes())
        except Exception:  # noqa: BLE001 -- unresolvable annotations are not errors
            return None
    except Exception:  # noqa: BLE001 -- unresolvable annotations are not errors
        return None
    hint = hints.get("return")
    resolved = resolve_hint(hint)
    if resolved is not None:
        return resolved
    if (
        owner is not None
        and owner.__module__ == "auto_3dx.geometry.query"
        and isinstance(hint, typing.TypeVar)
    ):
        return ("inst", owner)
    return None


def _auto_3dx_subclasses(cls: type) -> "list[type]":
    """Lists every auto_3dx subclass of `cls`, depth first."""
    found: "list[type]" = []
    for subclass in cls.__subclasses__():
        if subclass.__module__.startswith("auto_3dx"):
            found.append(subclass)
            found.extend(_auto_3dx_subclasses(subclass))
    return found


class ApiChecker:
    """Walks example code and checks it against the installed auto_3dx package."""

    def __init__(self, root_exports: set[str], label: str) -> None:
        self.root_exports = root_exports
        self.label = label
        self.env: dict[str, Inferred] = {}
        self.errors: list[str] = []
        self.checked = 0

    def fail(self, node: ast.AST, message: str) -> None:
        self.errors.append(f"{self.label}:{getattr(node, 'lineno', '?')}: {message}")

    # Statements ------------------------------------------------------------------

    def block(self, statements: list[ast.stmt]) -> None:
        for statement in statements:
            self.statement(statement)

    def statement(self, node: ast.stmt) -> None:
        if isinstance(node, ast.ImportFrom):
            self.import_from(node)
        elif isinstance(node, ast.Import):
            self.import_modules(node)
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            value = self.expr(node.value)
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                self.bind_target(target, value)
        elif isinstance(node, ast.With):
            for item in node.items:
                context = self.expr(item.context_expr)
                if item.optional_vars is not None:
                    self.bind_target(item.optional_vars, self.entered(context))
            self.block(node.body)
        elif isinstance(node, ast.For):
            iterable = self.expr(node.iter)
            item = iterable[1] if iterable and iterable[0] == "seq" else None
            self.bind_target(node.target, item)
            self.block(node.body)
            self.block(node.orelse)
        elif isinstance(node, ast.Try):
            self.block(node.body)
            for handler in node.handlers:
                self.expr(handler.type)
                if handler.name:
                    self.env[handler.name] = None
                self.block(handler.body)
            self.block(node.orelse)
            self.block(node.finalbody)
        elif isinstance(node, (ast.If, ast.While)):
            self.expr(node.test)
            self.block(node.body)
            self.block(node.orelse)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            self.block(node.body)
        else:
            for child in ast.iter_child_nodes(node):
                if isinstance(child, ast.expr):
                    self.expr(child)

    def bind_target(self, target: ast.expr, value: Inferred) -> None:
        if isinstance(target, ast.Name):
            self.env[target.id] = value
            return
        if isinstance(target, (ast.Tuple, ast.List)):
            item = value[1] if value and value[0] == "seq" else None
            for element in target.elts:
                self.bind_target(element, item)
            return
        self.expr(target)

    def entered(self, context: Inferred) -> Inferred:
        """Returns the type a `with` statement binds for a context expression."""
        if context and context[0] == "seq":
            return context[1]
        if context and context[0] == "inst":
            enter = inspect.getattr_static(context[1], "__enter__", None)
            return return_type(enter) if inspect.isfunction(enter) else None
        return None

    def import_from(self, node: ast.ImportFrom) -> None:
        module_name = node.module or ""
        if not module_name.startswith("auto_3dx"):
            return
        try:
            module = importlib.import_module(module_name)
        except ImportError as error:
            self.fail(node, f"cannot import {module_name}: {error}")
            return
        for alias in node.names:
            if module_name == "auto_3dx" and alias.name not in self.root_exports:
                self.fail(
                    node,
                    f"{alias.name} is not a package-root export; import it from its own package",
                )
            value = getattr(module, alias.name, MISSING)
            if value is MISSING:
                self.fail(node, f"{module_name} has no name {alias.name!r}")
                continue
            self.checked += 1
            self.env[alias.asname or alias.name] = self.wrap(value)

    def import_modules(self, node: ast.Import) -> None:
        for alias in node.names:
            if not alias.name.startswith("auto_3dx"):
                continue
            try:
                module = importlib.import_module(alias.name)
            except ImportError as error:
                self.fail(node, f"cannot import {alias.name}: {error}")
                continue
            if alias.asname:
                self.env[alias.asname] = ("mod", module)
            else:
                self.env[alias.name.split(".")[0]] = ("mod", importlib.import_module("auto_3dx"))

    @staticmethod
    def wrap(value: Any) -> Inferred:
        if inspect.isclass(value):
            return ("cls", value)
        if inspect.ismodule(value):
            return ("mod", value)
        return None

    # Expressions -----------------------------------------------------------------

    def expr(self, node: ast.AST | None) -> Inferred:
        if node is None:
            return None
        if isinstance(node, ast.Name):
            return self.env.get(node.id)
        if isinstance(node, ast.Attribute):
            return self.attribute(node)
        if isinstance(node, ast.Call):
            return self.call(node)
        if isinstance(node, ast.Subscript):
            self.expr(node.slice)
            base = self.expr(node.value)
            if base and base[0] == "seq":
                return base[1]
            if base and base[0] == "inst":
                getitem = inspect.getattr_static(base[1], "__getitem__", None)
                return return_type(getitem) if inspect.isfunction(getitem) else None
            return None
        if isinstance(node, (ast.ListComp, ast.SetComp, ast.GeneratorExp, ast.DictComp)):
            return self.comprehension(node)
        for child in ast.iter_child_nodes(node):
            self.expr(child)
        return None

    def comprehension(
        self, node: ast.ListComp | ast.SetComp | ast.GeneratorExp | ast.DictComp
    ) -> Inferred:
        """Checks a comprehension with its loop variables typed, without leaking them."""
        saved = dict(self.env)
        for generator in node.generators:
            iterable = self.expr(generator.iter)
            item = iterable[1] if iterable and iterable[0] == "seq" else None
            self.bind_target(generator.target, item)
            for condition in generator.ifs:
                self.expr(condition)
        if isinstance(node, ast.DictComp):
            self.expr(node.key)
            self.expr(node.value)
        else:
            self.expr(node.elt)
        self.env = saved
        return None

    def attribute(self, node: ast.Attribute) -> Inferred:
        if node.attr in RETIRED_NAMES:
            self.fail(node, f"{node.attr!r} is retired: {RETIRED_NAMES[node.attr]}")
        owner = self.expr(node.value)
        if not owner or owner[0] not in {"inst", "cls", "mod"}:
            return None
        if owner[0] == "mod":
            value = getattr(owner[1], node.attr, MISSING)
            if value is MISSING:
                self.fail(node, f"{owner[1].__name__} has no name {node.attr!r}")
                return None
            self.checked += 1
            return self.wrap(value)
        cls = owner[1]
        # Dataclass fields first: a field with a default is also a class attribute
        # holding that default, which would hide the field's annotated type.
        if dataclasses.is_dataclass(cls) and node.attr in {f.name for f in dataclasses.fields(cls)}:
            self.checked += 1
            try:
                return resolve_hint(typing.get_type_hints(cls).get(node.attr))
            except Exception:  # noqa: BLE001
                return None
        static = inspect.getattr_static(cls, node.attr, MISSING)
        if static is MISSING:
            # A lookup typed as a base class (`planes.get()` -> `Plane`) may return a
            # subclass (`OffsetPlane`); accept a member any auto_3dx subclass defines.
            for subclass in _auto_3dx_subclasses(cls):
                static = inspect.getattr_static(subclass, node.attr, MISSING)
                if static is not MISSING:
                    cls = subclass
                    break
        if static is MISSING:
            self.fail(node, f"{cls.__name__} has no member {node.attr!r}")
            return None
        self.checked += 1
        if isinstance(static, property):
            return return_type(static.fget)
        if inspect.isfunction(static) or isinstance(static, (classmethod, staticmethod)):
            return ("method", cls, node.attr, static, owner[0])
        return None

    def call(self, node: ast.Call) -> Inferred:
        for argument in node.args:
            self.expr(argument.value if isinstance(argument, ast.Starred) else argument)
        for keyword in node.keywords:
            self.expr(keyword.value)
        target = self.expr(node.func)
        if not target:
            return None
        if target[0] == "cls":
            return ("inst", target[1])
        if target[0] != "method":
            return None
        _, cls, name, static, owner_kind = target
        function = static.__func__ if isinstance(static, (classmethod, staticmethod)) else static
        self.bind_arguments(node, cls, name, static, function, owner_kind)
        return return_type(function, cls)

    def bind_arguments(
        self, node: ast.Call, cls: type, name: str, static: Any, function: Any, owner_kind: str
    ) -> None:
        if any(isinstance(arg, ast.Starred) for arg in node.args):
            return
        if any(keyword.arg is None for keyword in node.keywords):
            return
        needs_first = isinstance(static, classmethod) or (
            inspect.isfunction(static) and owner_kind == "inst"
        )
        try:
            signature = inspect.signature(function)
        except (TypeError, ValueError):
            return
        positional = [None] * (len(node.args) + (1 if needs_first else 0))
        keywords = {keyword.arg: None for keyword in node.keywords}
        try:
            signature.bind(*positional, **keywords)
        except TypeError as error:
            self.fail(node, f"{cls.__name__}.{name}{signature} rejects this call: {error}")


def check_code(source: str, label: str, root_exports: set[str]) -> tuple[list[str], int]:
    """Checks every python block in one Markdown document.

    Blocks are checked in order and share names, as a reader would run them.

    Returns:
        The failure messages and how many names were checked.
    """
    checker = ApiChecker(root_exports, label)
    for match in CODE_BLOCK.finditer(source):
        first_line = source.count("\n", 0, match.start(1))
        try:
            tree = ast.parse(match.group(1))
        except SyntaxError as error:
            checker.errors.append(
                f"{label}:{first_line + (error.lineno or 0)}: syntax error: {error.msg}"
            )
            continue
        ast.increment_lineno(tree, first_line)
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                module_names = (
                    [alias.name for alias in node.names]
                    if isinstance(node, ast.Import) else [node.module or ""]
                )
                for module_name in module_names:
                    if module_name.startswith(
                        ("win32com", "com3dx", "auto_3dx._", "auto_3dx.transport")
                    ):
                        checker.fail(node, f"raw COM or private SDK import {module_name!r}")
            if isinstance(node, ast.Name) and node.id in FORBIDDEN_EXAMPLE_NAMES:
                checker.fail(node, f"raw COM or private SDK name {node.id!r} in an example")
            if isinstance(node, ast.Attribute) and node.attr in FORBIDDEN_EXAMPLE_NAMES:
                checker.fail(node, f"raw COM or private SDK member {node.attr!r} in an example")
            if isinstance(node, ast.Attribute) and node.attr.startswith("_"):
                checker.fail(node, f"private member {node.attr!r} in an example")
        checker.block(tree.body)
    return checker.errors, checker.checked


def check_public_symbols() -> tuple[list[str], int]:
    """Checks the documented Phase 5 and SDK v1 public entry points exist in this SDK."""
    failures: list[str] = []
    checked = 0
    for symbol in PHASE5_PUBLIC_SYMBOLS + SDK_V1_PUBLIC_SYMBOLS:
        module_name, class_name, member_name = symbol.rsplit(".", 2)
        try:
            module = importlib.import_module(module_name)
            cls = getattr(module, class_name)
            member = inspect.getattr_static(cls, member_name)
        except (ImportError, AttributeError) as error:
            failures.append(f"Public symbol {symbol} is unavailable: {error}")
            continue
        if f"{class_name}.{member_name}" in SETTABLE_SYMBOLS:
            if not isinstance(member, property) or member.fset is None:
                failures.append(f"Public symbol {symbol} is not writable.")
        checked += 1
    return failures, checked


def check_api() -> tuple[str, list[str], int, int]:
    """Runs the API check, or reports it as skipped when auto_3dx is unavailable."""
    try:
        auto_3dx = importlib.import_module("auto_3dx")
    except ImportError:
        return "SKIPPED", ["auto_3dx is not importable in this environment."], 0, 0
    failures: list[str] = []
    checked = 0
    symbol_failures, symbol_count = check_public_symbols()
    failures.extend(symbol_failures)
    checked += symbol_count
    for relative in CODE_FILES:
        errors, count = check_code(read_text(SKILL_DIR / relative), relative, set(auto_3dx.__all__))
        failures.extend(errors)
        checked += count
    if checked == 0:
        failures.append("No auto_3dx names were checked; the examples could not be analysed.")
    status = "FAIL" if failures else "PASS"
    return status, failures, checked, symbol_count


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--require-sdk",
        action="store_true",
        help="fail instead of skipping the API check when auto_3dx is not importable",
    )
    arguments = parser.parse_args()

    version = ".".join(str(part) for part in sys.version_info[:3])
    print(f"interpreter: {sys.executable} (Python {version})")
    auto_3dx_spec = importlib.util.find_spec("auto_3dx")
    print(f"auto_3dx: {auto_3dx_spec.origin if auto_3dx_spec else 'not installed'}")

    document_failures = check_document()
    print(f"document contract: {'FAIL' if document_failures else 'PASS'}")
    for failure in document_failures:
        print(f"  - {failure}")

    status, api_messages, checked, symbol_count = check_api()
    detail = (
        f" ({checked} names checked: {symbol_count} explicit symbols, "
        f"{checked - symbol_count} example references)"
        if status != "SKIPPED" else ""
    )
    print(f"api check: {status}{detail}")
    for message in api_messages:
        print(f"  - {message}")
    skipped_but_required = status == "SKIPPED" and arguments.require_sdk
    if skipped_but_required:
        print("  - --require-sdk: a skipped API check is a failure.")

    return 1 if document_failures or status == "FAIL" or skipped_but_required else 0


if __name__ == "__main__":
    sys.exit(main())
