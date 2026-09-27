# auto-3dx-skill

The agent skill for [auto-3dx](https://github.com/2ssunny/auto-3dx), the Python
SDK that drives a running 3DEXPERIENCE CATIA session over Windows COM.

The skill is the operating contract an AI coding agent follows when it uses the
SDK: attach to the session, inspect the open Part, make one logical change
through the public API, rebuild explicitly, verify, and recover safely — without
raw COM, without saving, and without bypassing the SDK's safety checks.

**This repository is the single source of truth for the `auto-3dx` skill.** Edit
the skill here and nowhere else. Agents and other repositories expose it by
linking to a local checkout, never by copying it.

## Repositories

| Repository | Responsibility |
|---|---|
| [`2ssunny/auto-3dx`](https://github.com/2ssunny/auto-3dx) | The SDK: source, public API, tests, SDK documentation |
| `2ssunny/auto-3dx-skill` (this one) | How an agent should use the SDK: `SKILL.md`, references, examples, validator, agent metadata |
| [`2ssunny/auto-3dx-benchmark`](https://github.com/2ssunny/auto-3dx-benchmark) | Correctness and performance benchmark and oracle |
| [`2ssunny/ai-agents`](https://github.com/2ssunny/ai-agents) | Generic rules and skills, plus the linker that registers this skill as an external skill |

The skill documents the SDK; it does not define it. **When the skill and the
installed `auto_3dx` package disagree, the package wins** — follow the package
and report the drift. A capability the SDK lacks is a finding to report, not
permission to fall back to raw COM.

## Layout

```
SKILL.md              entry point: frontmatter (name, description) + workflow and core rules
agents/openai.yaml    display metadata for Codex
references/           detail loaded on demand (capabilities, safety, geometry queries,
                      topology, editing, Part Design, examples, upstream sync record)
scripts/validate_skill.py
                      document contract + API check against the installed SDK
```

## Supported agents

`SKILL.md` uses only the portable `name` and `description` frontmatter fields,
so the same folder works for every agent that reads the common skill format:

- **Claude Code** — reads skills from `~/.claude/skills/<name>/` (global) or
  `<project>/.claude/skills/<name>/`.
- **Codex** — reads skills from `~/.agents/skills/<name>/` or
  `<project>/.agents/skills/<name>/`; `agents/openai.yaml` supplies its display
  metadata.
- **Antigravity** — reads skill directories registered in
  `~/.gemini/config/skills.json`, or `<project>/.agents/skills/<name>/`.

Expose the skill under the name **`auto-3dx`** (the frontmatter name), whatever
the checkout folder is called.

## Installing

Clone this repository anywhere, then link it into the agents that should see it.
With [`2ssunny/ai-agents`](https://github.com/2ssunny/ai-agents), register the
checkout as an external skill in that repository's machine-local
`agent-config.json` and let its linker create the links:

```json
{
  "skills": {
    "external": {
      "auto-3dx": { "path": "<path-to-your-auto-3dx-skill-checkout>" }
    }
  }
}
```

See the ai-agents README for the global and per-project linking commands. Without
ai-agents, create the links yourself — a directory junction on Windows
(`mklink /J`), a symbolic link elsewhere (`ln -s`) — named `auto-3dx`. Agents
pick up new skills from their next session.

## Validating

Run the validator with the Python interpreter whose `auto_3dx` installation you
want to check — the project's venv, a Conda environment, or any other Python:

```bash
python scripts/validate_skill.py
```

It runs two checks and prints which interpreter and which `auto_3dx` it used:

1. **Document contract** (standard library only): frontmatter keys and name,
   `SKILL.md` length, every relative Markdown link resolves inside the
   repository, no machine-specific user paths, no reference to the skill's
   retired location.
2. **API check** (needs `auto_3dx` importable): every Python example in
   `SKILL.md` and the code-bearing references is checked against the installed
   package — members exist, arguments bind to real signatures, package-root
   imports come from `auto_3dx.__all__`, and no retired name is taught.

Without `auto_3dx` the API check reports **SKIPPED**, which is not a pass. The
validator never searches for another interpreter.

## SDK compatibility

[`references/upstream-sync.md`](references/upstream-sync.md) records the SDK
state the skill was last reviewed against — upstream commit, phase, package
version, test evidence — and the procedure for the next sync. Nothing in the
skill depends on that commit at runtime; the installed package is always
authoritative. When the SDK changes, review its diff since the recorded commit,
update the smallest affected part of the skill, re-run the validator against the
new installation, and update the record.

## History

The skill was first developed inside `2ssunny/ai-agents` as an embedded global
skill. Its history there was extracted with `git subtree split` and merged into
this repository with the original commits, authors and dates intact; ai-agents
now only links to a checkout of this repository.
