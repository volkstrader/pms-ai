---
title: pms-ai — plugin + config core — implementation plan
status: Draft (2026-06-01)
created: 2026-06-01
subsystem: 1 of 4
spec: docs/superpowers/specs/2026-05-31-pms-ai-plugin-config-core-design.md
reference: a prior internal reference implementation ("agenthq"), kept private — not a dependency
---

# pms-ai — Plugin + Config Core — Implementation Plan

Turns the **Approved** spec
(`docs/superpowers/specs/2026-05-31-pms-ai-plugin-config-core-design.md`) into an ordered,
verifiable build. This plan covers **subsystem #1 only**: the marketplace-plugin shell + the
configuration core every later subsystem stands on. Nothing here touches subsystems #2–#4.

## Outcome

After this plan is executed, a fresh clone supports the full config lifecycle end-to-end:

- The repo is installable as a Claude Code marketplace plugin (and is its own marketplace).
- `/onboard` (and `pms-ai onboard`) bootstraps `~/.pms-ai/{key}/config.yaml` for exactly one org.
- `pms-ai use <project>` switches the active context; `pms-ai show` reports config + resolved
  project and surfaces required-secret status read **only** from the environment.
- `pms_ai.config` is the single source of truth; the skill, command, and CLI all wrap it.
- Unit tests prove the config lifecycle under a `PMS_AI_HOME` temp dir; repo hygiene is verified.

## Decisions locked at planning time

The spec left these explicitly to the plan ("not architecturally significant"):

| Decision | Choice | Why |
|----------|--------|-----|
| Config validation | **pydantic v2** | Typed model, clear validation errors, matches spec recommendation. |
| YAML I/O | **ruamel.yaml** | Round-trip preservation so `use()` rewrites *only* `current_project`, keeping comments/formatting. |
| CLI framework | **argparse (stdlib)** | Thin command surface; zero extra runtime dep for the CLI layer. |
| Build backend | **hatchling**, `src/` layout | Standard, minimal `pyproject.toml`; clean wheel of `src/pms_ai`. |
| `/onboard` UX | Collect **one-or-more** projects at bootstrap; the `config` skill helps add more later. | First project becomes `current_project`; matches the `projects:` map shape; avoids a premature `add` subcommand. |
| `organization.key` rule | `^[a-zA-Z]+$`, length ≤ 32 | "Short, alphabetic, spaceless," safe as an on-disk dir name; satisfies the "reject spaces/non-alpha" verification. |
| Required secret (demo) | `PMS_AI_TOKEN` (documented in `.env.schema`) | Gives `pms-ai show` a real env-only key to read so the secrets verification is exercisable; never committed. |

## Runtime dependencies

- `pydantic>=2`
- `ruamel.yaml>=0.18`
- dev: `pytest>=8`

> Pre-flight: confirm `pydantic` and `ruamel.yaml` are installable in this environment before
> Phase 2 (neither is currently importable). If the network policy blocks PyPI, escalate the
> contingency in "Risks" rather than silently switching libraries — the round-trip rewrite
> guarantee depends on ruamel.

## Target repo layout (delta over current tree)

```
pms-ai/
  .claude-plugin/
    plugin.json                 # NEW — plugin manifest
    marketplace.json            # NEW — self-hosting marketplace (source ".")
  commands/
    onboard.md                  # NEW — /onboard slash command
  skills/
    config/
      SKILL.md                  # NEW — owns template + config-management guidance
      config.template.yaml      # NEW — committed template /onboard renders from
  src/pms_ai/
    __init__.py                 # NEW — package + version
    config.py                   # NEW — SINGLE SOURCE OF TRUTH
    cli.py                      # NEW — `pms-ai` console script
  tests/
    test_config.py              # NEW — config lifecycle unit tests
  .env.schema                   # NEW — varlock schema (names only, non-secret)
  .env.example                  # NEW — documents required env var names
  pyproject.toml                # NEW — project + console-script + deps
  (existing) .gitignore CLAUDE.md LICENSE README.md docs/
```

## `pms_ai.config` — public interface (the contract everything wraps)

```python
DEFAULT_HOME = "~/.pms-ai"
KEY_RE       = re.compile(r"^[a-zA-Z]+$")   # short + alphabetic + spaceless

class ConfigError(Exception): ...           # raised with actionable, user-facing messages

# pydantic models
class Organization(BaseModel):  key: str; name: str
class Project(BaseModel):       repo: str                     # raw, as stored (~ / ${VAR} kept)
class Config(BaseModel):
    organization: Organization
    current_project: str | None = None
    projects: dict[str, Project] = {}
class ResolvedProject(BaseModel): name: str; repo: Path       # expanded, absolute

def home() -> Path                                            # $PMS_AI_HOME or ~/.pms-ai, expanded
def load() -> Config                                          # find single org dir; parse+validate; else ConfigError("run /onboard first")
def resolve_project(name: str | None = None, *, config: Config | None = None) -> ResolvedProject
def use(name: str) -> None                                    # ruamel round-trip; rewrite ONLY current_project
def init(org_key: str, org_name: str, projects: dict[str, str],
         current_project: str | None = None) -> Path          # validate key; render template; refuse overwrite
```

**Resolution order** in `resolve_project`: `name` arg → `PMS_AI_PROJECT` env → `current_project` →
if still unset and exactly one project exists, use it → else `ConfigError`. Unknown name →
`ConfigError` listing known projects. `repo` is expanded via `expanduser` + `expandvars` then made
absolute.

**Single-org discovery** (`load`/`use`): scan immediate subdirs of `home()` for a `config.yaml`;
zero → "run /onboard first"; one → use it; more than one → `ConfigError` ("one install = one org").

**Template location** (`init`): `$PMS_AI_TEMPLATE` override, else
`Path(__file__).resolve().parents[2] / "skills/config/config.template.yaml"` (holds in-repo and in
the installed plugin cache, since the whole repo *is* the plugin). Load with ruamel to preserve the
header comments, set `organization`/`current_project`, populate `projects` (flow-style
`{ repo: ... }` entries), dump. Refuse to overwrite an existing config.

## Phased build

### Phase 0 — Pre-flight (deps + skeleton)
1. Verify `pydantic` and `ruamel.yaml` install/import; record versions. If blocked, stop and raise
   the contingency (see Risks) — do not substitute libraries silently.
2. Create `src/pms_ai/__init__.py` with `__version__ = "0.1.0"` and create empty `tests/`.

**Check:** `python -c "import pydantic, ruamel.yaml"` succeeds; `python -c "import pms_ai"` works
with `src` on `PYTHONPATH` (or after editable install in Phase 4).

### Phase 1 — Config core (`src/pms_ai/config.py`) + template
1. Write `skills/config/config.template.yaml`: header comments (machine-local, git-ignored, never
   commit), `organization.key`/`name` placeholders, empty `current_project`, `projects: {}` with an
   example comment.
2. Implement `pms_ai.config` per the interface above: models, `home`, `_find_org_dir`, `load`,
   `_expand_path`, `resolve_project`, `use`, `init`, `ConfigError`.
3. Keep it pure: no network, no secrets, no `print` (raise `ConfigError`; the CLI renders messages).

**Check:** import works; ad-hoc `init`→`load` round-trip under a temp `PMS_AI_HOME`.

### Phase 2 — Unit tests (`tests/test_config.py`)
Cover the spec's verification #2, each test pointing `PMS_AI_HOME` at `tmp_path`
(monkeypatch env). Cases:
- `init()` writes a valid `config.yaml`; `load()` round-trips it.
- `resolve_project()` honors precedence: `--project`/arg > `PMS_AI_PROJECT` > `current_project`;
  single-project fallback; unknown name → `ConfigError`.
- `use()` rewrites **only** `current_project` (assert other keys/comments untouched).
- `load()` on a missing config raises the "run /onboard first" error.
- `init()` rejects keys with spaces / non-alpha / over-length; refuses to overwrite.

**Check:** `pytest -q` green.

### Phase 3 — CLI (`src/pms_ai/cli.py`)
1. `argparse` with subcommands, all delegating to `pms_ai.config`:
   - `onboard` — flags (`--key`, `--name`, `--project name=repo` repeatable, `--current`) for
     non-interactive use; prompt interactively for any missing piece (collect one-or-more projects;
     first added becomes `current_project` unless `--current` given). Calls `init()`.
   - `use <project>` — calls `use()`; prints the new active context.
   - `show` — prints org, projects, resolved active project; then a **secrets** section that reads
     required names (`PMS_AI_TOKEN`) from `os.environ` only, printing present/masked or
     **missing**, and exits non-zero if any required secret is absent (`--skip-secrets` to bypass
     for config-only inspection).
   - `config …` — namespace alias surfacing the same read ops (at minimum `config show`).
2. `main()` maps `ConfigError` to a clean stderr message + non-zero exit (no tracebacks).
3. Console script `pms-ai = pms_ai.cli:main`.

**Check:** with a temp `PMS_AI_HOME` — `pms-ai onboard --key acme --name "Acme" --project
web=~/repos/acme-web`, then `pms-ai use web`, then `pms-ai show` (bare fails on missing
`PMS_AI_TOKEN`; `PMS_AI_TOKEN=x pms-ai show` succeeds).

### Phase 4 — Packaging (`pyproject.toml`) + plugin/marketplace manifests
1. `pyproject.toml`: `[project]` (name `pms-ai`, version, `requires-python>=3.10`, deps),
   `[project.scripts] pms-ai = "pms_ai.cli:main"`, `[project.optional-dependencies] dev`,
   hatchling build wiring `packages = ["src/pms_ai"]`.
2. `.claude-plugin/plugin.json`: name/version/description/author (commands/, skills/, agents/ are
   auto-discovered).
3. `.claude-plugin/marketplace.json`: marketplace `name`, `owner`, one plugin entry with
   `"source": "."` (self-hosting).

**Check:** `pip install -e .` exposes the `pms-ai` script; JSON manifests parse.

### Phase 5 — Plugin surfaces (skill + command)
1. `skills/config/SKILL.md`: frontmatter (`name: config`, trigger description); body explains the
   config model, points at the committed template, and instructs wrapping the CLI/module (never
   parse YAML inline) — including how to **add more projects** after onboarding.
2. `commands/onboard.md`: frontmatter `description`; body drives the interactive bootstrap by
   gathering org `key`/`name` + one-or-more `name=repo` projects and invoking `pms-ai onboard`
   (single source of truth), then confirms the written path.

**Check:** YAML frontmatter valid; both reference only `pms-ai`/`pms_ai.config`, never a second
YAML reader.

### Phase 6 — Secrets + hygiene
1. `.env.schema` (varlock): documents `PMS_AI_TOKEN` (required, sensitive) — names/specs only, no
   values.
2. `.env.example`: placeholder value, copy-to-`.env` note, mention `varlock run --` / `infisical
   run --` runtime injection.
3. Confirm `.gitignore` already ignores `.env.*` and **un-ignores** `.env.example`
   (lines 221–222 confirmed: `.env.*` then `!.env.example`).

**Check:** `git check-ignore .env` → ignored; `git check-ignore .env.example` → **not** ignored;
no secret values anywhere in the tree.

## End-to-end verification (maps 1:1 to spec §Verification)

1. **Packaging:** `/plugin marketplace add <path>` + `/plugin install` makes `/onboard` and
   `pms-ai` available (manual, documented for the reviewer).
2. **Config unit:** Phase 2 `pytest` green (init/load/resolve/use/missing-config).
3. **/onboard flow:** generates `~/.pms-ai/{key}/config.yaml` from the template; rejects bad keys;
   file lands outside any repo (machine-local).
4. **Secrets:** `pms-ai show` reads `PMS_AI_TOKEN` from env only; bare run fails clearly;
   `varlock run -- pms-ai show` / `infisical run -- pms-ai show` succeed.
5. **Hygiene:** `git check-ignore` confirms secret patterns ignored and `.env.example` tracked.

## Risks & contingencies

- **PyPI blocked by network policy.** ruamel/pydantic may not install. Contingency: surface to the
  user; options are (a) pre-provision the deps in the environment, or (b) vendor them — *not* switch
  to PyYAML, since comment-preserving rewrite is a spec requirement for `use()`.
- **Template path under installed plugin cache.** `parents[2]` assumes the `src/pms_ai/`↔`skills/`
  layout is preserved when Claude copies the plugin. Mitigated by the `$PMS_AI_TEMPLATE` override.
- **`pms-ai show` strictness vs convenience.** Requiring `PMS_AI_TOKEN` could annoy config-only
  use; mitigated by `--skip-secrets`. Unit tests exercise the config module directly, so CLI
  secret-strictness never blocks the test suite.

## Out of scope (explicit)

Staged-project/artifact model (#2), workflow engine (#3), visualization (#4), and any `agents/`
primitives — each gets its own brainstorm → spec → plan cycle per the roadmap.

## Suggested commit sequence

1. `plan: subsystem #1 implementation plan` (this file).
2. `feat(config): pms_ai.config single source of truth + tests` (Phases 1–2).
3. `feat(cli): pms-ai onboard/use/show over pms_ai.config` (Phase 3).
4. `build: pyproject + plugin/marketplace manifests` (Phase 4).
5. `feat(plugin): config skill + /onboard command + template` (Phases 1/5).
6. `chore(secrets): .env.schema + .env.example + hygiene checks` (Phase 6).
