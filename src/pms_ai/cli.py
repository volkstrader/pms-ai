"""pms-ai — thin CLI over :mod:`pms_ai.config` (the single source of truth).

Subcommands: ``onboard`` (bootstrap an org + projects), ``use`` (switch the
active project), ``show`` (print config + resolved project + secret status).
``config show`` mirrors ``show``. The CLI never parses config itself — every
operation delegates to :mod:`pms_ai.config`.

Secrets are read from ``os.environ`` only; inject them at runtime with
``varlock run -- pms-ai ...`` or ``infisical run -- pms-ai ...``.
"""

from __future__ import annotations

import argparse
import os
import sys

from . import __version__, config

#: Required secret names, read env-only. Documented (names only) in .env.schema.
REQUIRED_SECRETS = ("PMS_AI_TOKEN",)


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def _parse_project_args(specs: list[str]) -> dict[str, str]:
    """Parse repeated ``NAME=REPO`` specs into an ordered ``{name: repo}`` map."""
    projects: dict[str, str] = {}
    for spec in specs:
        if "=" not in spec:
            raise config.ConfigError(
                f"bad --project {spec!r}; expected NAME=REPO (e.g. web=~/repos/acme-web)"
            )
        name, repo = spec.split("=", 1)
        name, repo = name.strip(), repo.strip()
        if not name or not repo:
            raise config.ConfigError(f"bad --project {spec!r}; both NAME and REPO are required")
        projects[name] = repo
    return projects


def _prompt(label: str, *, required: bool = True) -> str:
    """Read a trimmed line from stdin, re-prompting while ``required`` and blank."""
    while True:
        value = input(f"{label}: ").strip()
        if value or not required:
            return value
        print("  (required)", file=sys.stderr)


def _missing_secrets() -> list[str]:
    """Return required secret names absent from the environment."""
    return [name for name in REQUIRED_SECRETS if not os.environ.get(name)]


# --------------------------------------------------------------------------- #
# commands
# --------------------------------------------------------------------------- #
def cmd_onboard(args: argparse.Namespace) -> int:
    """Bootstrap the org config, prompting for anything not supplied via flags."""
    projects = _parse_project_args(args.project)
    key = args.key
    name = args.name

    if args.non_interactive:
        if not (key and name and projects):
            raise config.ConfigError(
                "--non-interactive requires --key, --name, and at least one --project NAME=REPO"
            )
    else:
        # interactive bootstrap: prompt for anything not supplied via flags
        key = key or _prompt("Organization key (short, letters only, e.g. acme)")
        name = name or _prompt("Organization name (full, human-readable)")
        if not projects:
            print("Add one or more projects (blank name to finish):")
            while True:
                pname = _prompt("  project name", required=not projects)
                if not pname:
                    break
                repo = _prompt(f"  repo path for {pname!r}")
                projects[pname] = repo

    path = config.init(key, name, projects, current_project=args.current)
    print(f"Wrote {path}")
    print(f"Active project: {config.load().current_project}")
    return 0


def cmd_use(args: argparse.Namespace) -> int:
    """Set the active project (delegates to ``config.use``)."""
    config.use(args.project)
    print(f"Active project: {args.project}")
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    """Print the org, projects, resolved active project, and env-secret status.

    Returns a non-zero exit code if a required secret is missing (unless
    ``--skip-secrets``).
    """
    cfg = config.load()
    print(f"organization: {cfg.organization.name} ({cfg.organization.key})")
    print("projects:")
    for pname, project in cfg.projects.items():
        marker = "*" if pname == cfg.current_project else " "
        print(f"  {marker} {pname}: {project.repo}")

    try:
        active = config.resolve_project(getattr(args, "project", None), config=cfg)
        print(f"active: {active.name} -> {active.repo}")
    except config.ConfigError as exc:
        print(f"active: (unresolved) {exc}")

    if getattr(args, "skip_secrets", False):
        return 0

    missing = _missing_secrets()
    print("secrets (env-only):")
    for secret in REQUIRED_SECRETS:
        status = "MISSING" if secret in missing else "set"
        print(f"  {secret}: {status}")
    if missing:
        print(
            "missing required secret(s); inject with `varlock run -- pms-ai show` or "
            "`infisical run -- pms-ai show`",
            file=sys.stderr,
        )
        return 1
    return 0


# --------------------------------------------------------------------------- #
# parser
# --------------------------------------------------------------------------- #
def build_parser() -> argparse.ArgumentParser:
    """Build the argparse parser for the ``pms-ai`` CLI and its subcommands."""
    parser = argparse.ArgumentParser(prog="pms-ai", description="pms-ai configuration CLI")
    parser.add_argument("--version", action="version", version=f"pms-ai {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p_onboard = sub.add_parser("onboard", help="bootstrap this install's org + projects")
    p_onboard.add_argument("--key", help="organization key (short, letters only)")
    p_onboard.add_argument("--name", help="full organization name")
    p_onboard.add_argument(
        "--project", action="append", default=[], metavar="NAME=REPO",
        help="add a project (repeatable)",
    )
    p_onboard.add_argument("--current", help="which project to make active (default: first)")
    p_onboard.add_argument(
        "--non-interactive", action="store_true", help="fail instead of prompting for missing input"
    )
    p_onboard.set_defaults(func=cmd_onboard)

    p_use = sub.add_parser("use", help="set the active project (rewrites current_project)")
    p_use.add_argument("project", help="project name to make active")
    p_use.set_defaults(func=cmd_use)

    p_show = sub.add_parser("show", help="print config, resolved project, and secret status")
    p_show.add_argument("--project", help="resolve a specific project instead of the active one")
    p_show.add_argument("--skip-secrets", action="store_true", help="skip the env-secret check")
    p_show.set_defaults(func=cmd_show)

    p_config = sub.add_parser("config", help="config operations")
    config_sub = p_config.add_subparsers(dest="config_command", required=True)
    p_config_show = config_sub.add_parser("show", help="alias for `pms-ai show`")
    p_config_show.add_argument("--project")
    p_config_show.add_argument("--skip-secrets", action="store_true")
    p_config_show.set_defaults(func=cmd_show)

    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entry point: dispatch the subcommand, mapping ConfigError to exit 2."""
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except config.ConfigError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except (KeyboardInterrupt, EOFError):  # pragma: no cover - interactive abort
        print("\naborted", file=sys.stderr)
        return 130


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
