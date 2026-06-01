# pms-ai

**A staging ground for projects; dynamic multi-agent workflows are the execution engine.**
You stage a project inside pms-ai — its identity, config, requirements, plan, and artifacts — and
a dynamically-composed workflow reads that staged state and drives the work to completion. pms-ai
is the durable control plane; workflows are ephemeral execution.

It is distributed as a **clean public Claude Code marketplace plugin** with a **vendored Python
CLI** (`pms-ai`). The repo is **both** the plugin and its own marketplace — no fork; per-org
variation is config + data the plugin reads.

> **Status:** subsystem #1 of 4 (plugin shell + config core). See
> [`docs/superpowers/specs/`](docs/superpowers/specs/) for the design and roadmap.

## Install (Claude Code plugin)

The repo self-hosts its marketplace, so installing is two slash commands inside Claude Code:

```text
/plugin marketplace add volkstrader/pms-ai
/plugin install pms-ai@pms-ai
```

- `marketplace add` registers this repo as a marketplace. You can pass a GitHub `owner/repo`
  shorthand (as above), a full git URL (`https://github.com/volkstrader/pms-ai.git`), or a local
  path to a clone.
- `pms-ai@pms-ai` is `<plugin>@<marketplace>` — both are named `pms-ai` here.

After install, the `/onboard` command and the `config` skill are available, and the bundled
`pms-ai` CLI ships with the plugin.

**Updating:** there is no fork to maintain — pull new versions with `/plugin update pms-ai`.

**Removing:**

```text
/plugin uninstall pms-ai@pms-ai
/plugin marketplace remove pms-ai
```

## The `pms-ai` CLI

The vendored CLI is the single source of truth for config (`pms_ai.config`); the `/onboard`
command and `config` skill wrap it. To run it directly (e.g. for development), install the Python
package:

```bash
pip install -e .          # exposes the `pms-ai` console script
```

### Quick start

```bash
# Bootstrap this install's organization + project(s) — one install = one org.
pms-ai onboard --key acme --name "Acme Corporation" --project web=~/repos/acme-web
# (run `pms-ai onboard` with no flags for an interactive prompt)

pms-ai use web            # switch the active project (rewrites current_project)
pms-ai show               # print org, projects, the resolved active project, + secret status
```

This writes a **machine-local, git-ignored** config to `~/.pms-ai/{key}/config.yaml`
(override the root with `PMS_AI_HOME`). The active project resolves in this order:
`--project` flag → `PMS_AI_PROJECT` → `current_project` → the sole project if only one exists.

## Secrets — env-only

pms-ai reads `os.environ` only; it never stores secrets. Inject them at runtime with your tool of
choice:

```bash
varlock run   -- pms-ai show
infisical run -- pms-ai show
```

The repo commits a non-secret [`.env.schema`](.env.schema) (variable **names** only) and
[`.env.example`](.env.example); resolved secrets are never committed.

## Development

```bash
pip install -e ".[dev]"
pytest
```

## License

See [LICENSE](LICENSE).
