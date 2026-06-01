"""pms_ai.config — the single source of truth for pms-ai configuration.

This module is the *only* code that knows the config schema and on-disk
locations. The ``config`` skill, the ``/onboard`` command, and the ``pms-ai``
CLI all wrap it; they never parse or write ``config.yaml`` themselves.

It is pure: no network, no secrets, no printing. Failures raise
:class:`ConfigError` with an actionable, user-facing message; callers (the CLI)
decide how to render them.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

from pydantic import BaseModel
from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap

__all__ = [
    "ConfigError",
    "Organization",
    "Project",
    "Config",
    "ResolvedProject",
    "home",
    "load",
    "resolve_project",
    "use",
    "init",
]

DEFAULT_HOME = "~/.pms-ai"

#: ``organization.key`` doubles as the on-disk directory name: short, alphabetic,
#: spaceless. Length is bounded separately for a clearer error message.
KEY_RE = re.compile(r"^[a-zA-Z]+$")
KEY_MAX_LEN = 32

#: Project names are kebab/snake slugs (folder-as-entity convention).
PROJECT_NAME_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9_-]*$")

_NOT_ONBOARDED = (
    "no pms-ai config found; run /onboard (or `pms-ai onboard`) first to create "
    "~/.pms-ai/{key}/config.yaml"
)


class ConfigError(Exception):
    """A configuration problem with a message safe to show the user."""


# --------------------------------------------------------------------------- #
# Typed model
# --------------------------------------------------------------------------- #
class Organization(BaseModel):
    key: str
    name: str


class Project(BaseModel):
    repo: str  # stored verbatim (``~`` / ``${VAR}`` preserved for portability)


class Config(BaseModel):
    organization: Organization
    current_project: str | None = None
    projects: dict[str, Project] = {}


class ResolvedProject(BaseModel):
    name: str
    repo: Path  # expanded, absolute


# --------------------------------------------------------------------------- #
# Locations
# --------------------------------------------------------------------------- #
def home() -> Path:
    """Root for org config dirs: ``$PMS_AI_HOME`` or ``~/.pms-ai`` (expanded)."""
    return Path(os.environ.get("PMS_AI_HOME", DEFAULT_HOME)).expanduser()


def _template_path() -> Path:
    """The committed template ``/onboard`` renders from.

    ``$PMS_AI_TEMPLATE`` overrides; otherwise it sits at
    ``<plugin root>/skills/config/config.template.yaml`` relative to this file,
    a layout preserved both in-repo and in Claude's installed plugin cache.
    """
    override = os.environ.get("PMS_AI_TEMPLATE")
    if override:
        return Path(override).expanduser()
    return Path(__file__).resolve().parents[2] / "skills" / "config" / "config.template.yaml"


def _find_org_dir() -> Path:
    """Locate the single org dir under :func:`home` (one install = one org)."""
    root = home()
    if not root.is_dir():
        raise ConfigError(_NOT_ONBOARDED)
    candidates = sorted(
        (d for d in root.iterdir() if d.is_dir() and (d / "config.yaml").is_file()),
        key=lambda d: d.name,
    )
    if not candidates:
        raise ConfigError(_NOT_ONBOARDED)
    if len(candidates) > 1:
        names = ", ".join(d.name for d in candidates)
        raise ConfigError(
            f"multiple org configs found under {root} ({names}); one install = one org. "
            "Remove the extra directories or point PMS_AI_HOME at the one you want."
        )
    return candidates[0]


def _config_file() -> Path:
    return _find_org_dir() / "config.yaml"


def _yaml() -> YAML:
    y = YAML()
    y.preserve_quotes = True
    y.indent(mapping=2, sequence=4, offset=2)
    return y


def _expand_path(raw: str) -> Path:
    """Expand ``${VAR}`` then ``~`` and make the path absolute."""
    expanded = os.path.expanduser(os.path.expandvars(str(raw)))
    p = Path(expanded)
    return p if p.is_absolute() else (Path.cwd() / p)


def _projects_map(projects: dict[str, str]) -> CommentedMap:
    """Build a block map of ``name: { repo: ... }`` flow-style entries."""
    out = CommentedMap()
    for name, repo in projects.items():
        entry = CommentedMap()
        entry["repo"] = repo
        entry.fa.set_flow_style()
        out[name] = entry
    return out


# --------------------------------------------------------------------------- #
# Public operations
# --------------------------------------------------------------------------- #
def load() -> Config:
    """Find the single org config, parse and validate it."""
    path = _config_file()
    try:
        with path.open() as f:
            data = _yaml().load(f)
    except OSError as exc:  # pragma: no cover - unexpected fs error
        raise ConfigError(f"could not read {path}: {exc}") from exc
    if data is None:
        raise ConfigError(f"config at {path} is empty; re-run /onboard")
    try:
        return Config.model_validate(data)
    except Exception as exc:  # pydantic ValidationError -> user-facing
        raise ConfigError(f"invalid config at {path}: {exc}") from exc


def resolve_project(name: str | None = None, *, config: Config | None = None) -> ResolvedProject:
    """Resolve the active project to a name + absolute repo path.

    Order: ``name`` arg → ``$PMS_AI_PROJECT`` → ``current_project`` → the sole
    project if exactly one exists → :class:`ConfigError`.
    """
    cfg = config or load()
    chosen = name or os.environ.get("PMS_AI_PROJECT") or cfg.current_project
    if not chosen:
        if len(cfg.projects) == 1:
            chosen = next(iter(cfg.projects))
        else:
            raise ConfigError(
                "no active project: pass --project, set PMS_AI_PROJECT, or run "
                "`pms-ai use <name>` to set current_project"
            )
    if chosen not in cfg.projects:
        known = ", ".join(cfg.projects) or "(none)"
        raise ConfigError(f"unknown project {chosen!r}; known projects: {known}")
    return ResolvedProject(name=chosen, repo=_expand_path(cfg.projects[chosen].repo))


def use(name: str) -> None:
    """Rewrite **only** ``current_project`` in place (comment-preserving)."""
    path = _config_file()
    yaml = _yaml()
    with path.open() as f:
        data = yaml.load(f)
    projects = data.get("projects") or {}
    if name not in projects:
        known = ", ".join(projects) or "(none)"
        raise ConfigError(f"unknown project {name!r}; known projects: {known}")
    data["current_project"] = name
    with path.open("w") as f:
        yaml.dump(data, f)


def init(
    org_key: str,
    org_name: str,
    projects: dict[str, str],
    current_project: str | None = None,
) -> Path:
    """Validate inputs, render the template to ``home()/{org_key}/config.yaml``.

    Refuses to overwrite an existing config. Returns the written path.
    """
    if not KEY_RE.match(org_key or ""):
        raise ConfigError(
            f"invalid organization key {org_key!r}: use letters only, no spaces or "
            "punctuation (e.g. 'acme')"
        )
    if len(org_key) > KEY_MAX_LEN:
        raise ConfigError(
            f"organization key {org_key!r} is too long (max {KEY_MAX_LEN} characters)"
        )
    if not org_name or not org_name.strip():
        raise ConfigError("organization name must not be empty")
    if not projects:
        raise ConfigError("at least one project is required (name + repo path)")
    for pname in projects:
        if not PROJECT_NAME_RE.match(pname):
            raise ConfigError(
                f"invalid project name {pname!r}: start with a letter; letters, digits, "
                "'-' and '_' only"
            )
    if current_project is None:
        current_project = next(iter(projects))
    elif current_project not in projects:
        raise ConfigError(
            f"current_project {current_project!r} is not one of the given projects: "
            f"{', '.join(projects)}"
        )

    org_dir = home() / org_key
    path = org_dir / "config.yaml"
    if path.exists():
        raise ConfigError(
            f"config already exists at {path}; refusing to overwrite (edit it directly "
            "or use `pms-ai use <project>`)"
        )

    yaml = _yaml()
    with _template_path().open() as f:
        data = yaml.load(f)
    data["organization"]["key"] = org_key
    data["organization"]["name"] = org_name
    data["current_project"] = current_project
    data["projects"] = _projects_map(projects)

    org_dir.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        yaml.dump(data, f)
    return path
