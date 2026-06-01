"""Unit tests for pms_ai.config — the config lifecycle under a temp PMS_AI_HOME.

Maps to spec §Verification #2: init writes a valid config; load round-trips it;
resolve_project honors flag > env > current_project; use rewrites only
current_project; load on a missing config raises the run-/onboard error.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from pms_ai import config


@pytest.fixture(autouse=True)
def temp_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point PMS_AI_HOME at a temp dir and clear project-selection env vars."""
    monkeypatch.setenv("PMS_AI_HOME", str(tmp_path))
    monkeypatch.delenv("PMS_AI_PROJECT", raising=False)
    return tmp_path


def _seed(**projects: str) -> Path:
    projects = projects or {"web": "~/repos/acme-web"}
    return config.init("acme", "Acme Corporation", dict(projects))


# --------------------------------------------------------------------------- #
# init + load round-trip
# --------------------------------------------------------------------------- #
def test_init_writes_under_org_key_dir(temp_home: Path) -> None:
    path = _seed(web="~/repos/acme-web", infra="~/repos/acme-infra")
    assert path == temp_home / "acme" / "config.yaml"
    assert path.is_file()


def test_load_round_trips(temp_home: Path) -> None:
    _seed(web="~/repos/acme-web", infra="~/repos/acme-infra")
    cfg = config.load()
    assert cfg.organization.key == "acme"
    assert cfg.organization.name == "Acme Corporation"
    assert set(cfg.projects) == {"web", "infra"}
    # first project becomes current_project by default
    assert cfg.current_project == "web"
    assert cfg.projects["web"].repo == "~/repos/acme-web"


def test_init_refuses_overwrite(temp_home: Path) -> None:
    _seed()
    with pytest.raises(config.ConfigError, match="already exists"):
        _seed()


def test_template_header_is_preserved(temp_home: Path) -> None:
    path = _seed()
    text = path.read_text()
    assert "MACHINE-LOCAL" in text  # header comment carried over from the template


# --------------------------------------------------------------------------- #
# key / input validation
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("bad", ["has space", "with-dash", "digits123", "sym!", "", "a" * 33])
def test_init_rejects_bad_keys(temp_home: Path, bad: str) -> None:
    with pytest.raises(config.ConfigError):
        config.init(bad, "Name", {"web": "~/repos/web"})


def test_init_requires_a_project(temp_home: Path) -> None:
    with pytest.raises(config.ConfigError, match="at least one project"):
        config.init("acme", "Acme", {})


def test_init_rejects_bad_project_name(temp_home: Path) -> None:
    with pytest.raises(config.ConfigError, match="invalid project name"):
        config.init("acme", "Acme", {"bad name": "~/repos/x"})


def test_init_malformed_template_raises(
    temp_home: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    bad = tmp_path / "bad.template.yaml"
    bad.write_text("organization: [not, a, mapping]\n")
    monkeypatch.setenv("PMS_AI_TEMPLATE", str(bad))
    with pytest.raises(config.ConfigError, match="invalid config template"):
        config.init("acme", "Acme", {"web": "~/repos/web"})


# --------------------------------------------------------------------------- #
# resolve_project precedence
# --------------------------------------------------------------------------- #
def test_resolve_uses_current_project(temp_home: Path) -> None:
    _seed(web="~/repos/acme-web", infra="~/repos/acme-infra")
    resolved = config.resolve_project()
    assert resolved.name == "web"
    assert resolved.repo == Path.home() / "repos" / "acme-web"
    assert resolved.repo.is_absolute()


def test_resolve_arg_beats_env_and_current(
    temp_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _seed(web="~/repos/acme-web", infra="~/repos/acme-infra")
    monkeypatch.setenv("PMS_AI_PROJECT", "infra")
    assert config.resolve_project("web").name == "web"  # explicit arg wins


def test_resolve_env_beats_current(
    temp_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _seed(web="~/repos/acme-web", infra="~/repos/acme-infra")
    monkeypatch.setenv("PMS_AI_PROJECT", "infra")
    assert config.resolve_project().name == "infra"


def test_resolve_single_project_fallback(temp_home: Path) -> None:
    # one project, and we blank current_project to exercise the sole-project path
    config.init("acme", "Acme", {"only": "~/repos/only"})
    config.use("only")
    cfg = config.load()
    cfg.current_project = None
    assert config.resolve_project(config=cfg).name == "only"


def test_resolve_ambiguous_raises(temp_home: Path) -> None:
    config.init("acme", "Acme", {"web": "~/repos/web", "infra": "~/repos/infra"})
    cfg = config.load()
    cfg.current_project = None
    with pytest.raises(config.ConfigError, match="no active project"):
        config.resolve_project(config=cfg)


def test_resolve_unknown_raises(temp_home: Path) -> None:
    _seed()
    with pytest.raises(config.ConfigError, match="unknown project"):
        config.resolve_project("nope")


def test_resolve_expands_env_vars(
    temp_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CODE", "/srv/code")
    config.init("acme", "Acme", {"web": "${CODE}/acme-web"})
    assert config.resolve_project("web").repo == Path("/srv/code/acme-web")


# --------------------------------------------------------------------------- #
# use rewrites ONLY current_project
# --------------------------------------------------------------------------- #
def test_use_rewrites_only_current_project(temp_home: Path) -> None:
    path = _seed(web="~/repos/acme-web", infra="~/repos/acme-infra")
    before = path.read_text()
    config.use("infra")
    after = path.read_text()

    assert config.load().current_project == "infra"
    # everything except the current_project line is byte-for-byte unchanged
    diff = [
        (b, a)
        for b, a in zip(before.splitlines(), after.splitlines(), strict=True)
        if b != a
    ]
    assert len(diff) == 1
    assert diff[0][1].startswith("current_project:")
    assert "MACHINE-LOCAL" in after  # comments preserved


def test_use_unknown_raises(temp_home: Path) -> None:
    _seed()
    with pytest.raises(config.ConfigError, match="unknown project"):
        config.use("ghost")


# --------------------------------------------------------------------------- #
# missing config -> run /onboard first
# --------------------------------------------------------------------------- #
def test_load_missing_config_raises(temp_home: Path) -> None:
    with pytest.raises(config.ConfigError, match="/onboard"):
        config.load()


def test_multiple_org_dirs_raises(temp_home: Path) -> None:
    config.init("acme", "Acme", {"web": "~/repos/web"})
    # a second org dir under the same home violates one-install-one-org
    (temp_home / "other").mkdir()
    (temp_home / "other" / "config.yaml").write_text("organization: {key: other, name: O}\n")
    with pytest.raises(config.ConfigError, match="one install = one org"):
        config.load()
