"""Units: discovery, relscribe.toml, and reading and writing versions (docs/design.md, Units)."""

from __future__ import annotations

import json
import re
import string
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

PACKAGE_JSON = "package.json"
PYPROJECT = "pyproject.toml"
CONFIG = "relscribe.toml"

# Plain X.Y.Z without leading zeros: no pre-releases or build metadata (docs/design.md, Versioning).
_VERSION = re.compile(r"(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)")
_PLACEHOLDERS = {"name", "dir", "version"}
_BUMPS = {"major", "minor", "patch"}


class ConfigError(Exception):
    """A configuration problem. The CLI reports it as exit code 2."""


class NoUnitError(ConfigError):
    """No unit at all: no workspace, and no version in a root manifest."""


@dataclass(frozen=True)
class Sync:
    """Another file that repeats the version; group 1 of `pattern` holds it."""

    file: str
    pattern: re.Pattern[str]


@dataclass(frozen=True)
class Unit:
    path: str  # POSIX, relative to the repository root; "." for the root
    name: str
    dir: str
    manifest: str  # PACKAGE_JSON or PYPROJECT, inside the unit directory
    version: str
    tag: str = "{name}@{version}"
    changelog: bool = True
    exclude: tuple[str, ...] = ()
    sync: tuple[Sync, ...] = ()
    bump: dict[str, str] = field(default_factory=dict)  # overrides only; the defaults live with the bump rules

    def tag_name(self, version: str) -> str:
        return self.tag.format(name=self.name, dir=self.dir, version=version)


def discover(root: Path) -> list[Unit]:
    """Find the units under `root`, sorted by path, with their `relscribe.toml` settings applied."""
    root = Path(root)
    defaults, per_unit = _load_config(root)
    workspace = _workspace(root)
    if workspace is None:
        units = [_root_unit(root)]
    else:
        patterns, manifest = workspace
        units = [u for path in _members(root, patterns) if (u := _read_unit(root, path, manifest))]

    paths = {u.path for u in units}
    for path in per_unit:
        if path not in paths:
            raise ConfigError(f'{CONFIG}: [units."{path}"] matches no unit')
    return [_with_settings(u, {**defaults, **per_unit.get(u.path, {})}) for u in units]


def write_version(root: Path, unit: Unit, new: str) -> list[str]:
    """Set `unit`'s version to `new` in its manifest and `sync` files; return the files changed.

    Every file is checked before any is written, so a configuration error writes nothing.
    """
    if not _VERSION.fullmatch(new):
        raise ValueError(f"not a plain X.Y.Z version: {new!r}")
    base = Path(root) / unit.path
    texts: dict[Path, str] = {}

    manifest = base / unit.manifest
    text = _read(manifest)
    if unit.manifest == PACKAGE_JSON:
        start, end = _json_version_span(text)
    else:
        start, end = _toml_version_span(text, manifest)
    if text[start:end] != unit.version:
        raise ConfigError(f"{_rel(root, manifest)}: version changed since it was read")
    texts[manifest] = text[:start] + new + text[end:]
    if _manifest_version(manifest, texts[manifest]) != new:
        raise ConfigError(f"{_rel(root, manifest)}: could not rewrite the version")

    for sync in unit.sync:
        path = base / sync.file
        where = f"{_rel(root, path)}: sync pattern {sync.pattern.pattern!r}"
        if path not in texts:
            if not path.is_file():
                raise ConfigError(f"{where}: the file is missing")
            texts[path] = _read(path)
        text = texts[path]
        matches = list(sync.pattern.finditer(text))
        if not matches:
            raise ConfigError(f"{where}: matches nothing")
        for m in matches:
            if m.group(1) != unit.version:
                raise ConfigError(f"{where}: found {m.group(1)!r}, not the current version {unit.version}")
        for m in reversed(matches):
            text = text[: m.start(1)] + new + text[m.end(1) :]
        texts[path] = text

    for path, text in texts.items():
        with path.open("w", encoding="utf-8", newline="") as f:
            f.write(text)
    return [_rel(root, path) for path in texts]


# Discovery


def _workspace(root: Path) -> tuple[list[str], str] | None:
    """The member globs and their manifest name, from the first workspace file that declares members."""
    pnpm = root / "pnpm-workspace.yaml"
    if pnpm.is_file():
        patterns = _pnpm_packages(_read(pnpm))
        if patterns is not None:
            return patterns, PACKAGE_JSON

    package_json = root / PACKAGE_JSON
    if package_json.is_file():
        workspaces = _load_json(package_json).get("workspaces")
        if workspaces is not None:
            return _strings(workspaces, f"{PACKAGE_JSON}: `workspaces`"), PACKAGE_JSON

    pyproject = root / PYPROJECT
    if pyproject.is_file():
        uv = _load_toml(pyproject).get("tool", {}).get("uv", {}).get("workspace")
        if uv is not None:
            where = f"{PYPROJECT}: [tool.uv.workspace]"
            members = _strings(uv.get("members", []), f"{where} `members`")
            excluded = _strings(uv.get("exclude", []), f"{where} `exclude`")
            return members + ["!" + e for e in excluded], PYPROJECT
    return None


def _pnpm_packages(text: str) -> list[str] | None:
    """The top-level `packages` block list. Only this much YAML is read (docs/design.md, Architecture)."""
    lines = text.splitlines()
    for i, line in enumerate(lines):
        m = re.match(r"packages\s*:(.*)$", line)
        if not m:
            continue
        rest = m[1].strip()
        if rest and not rest.startswith("#"):
            raise ConfigError("pnpm-workspace.yaml: `packages` must be a block list (`- pattern` lines)")
        items = []
        for item in lines[i + 1 :]:
            stripped = item.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if not stripped.startswith("-"):
                if item[0].isspace():
                    raise ConfigError(f"pnpm-workspace.yaml: unsupported line under `packages`: {stripped!r}")
                break  # the next top-level key
            items.append(_yaml_scalar(stripped[1:]))
        return items
    return None


def _yaml_scalar(text: str) -> str:
    text = text.strip()
    if text[:1] in ("'", '"'):
        end = text.find(text[0], 1)
        return text[1:end] if end > 0 else text[1:]
    return re.split(r"\s+#", text, maxsplit=1)[0].strip()


def _members(root: Path, patterns: list[str]) -> list[str]:
    """Directories matched by the globs, minus those matched by `!` globs, sorted."""
    included: set[str] = set()
    excluded: set[str] = set()
    for pattern in patterns:
        target = excluded if pattern.startswith("!") else included
        pattern = _norm(pattern.removeprefix("!"))
        if pattern == ".":
            target.add(".")
            continue
        for path in root.glob(pattern):
            rel = path.relative_to(root)
            # Installed dependencies are never workspace members.
            if path.is_dir() and "node_modules" not in rel.parts:
                target.add(rel.as_posix())
    return sorted(included - excluded)


def _norm(path: str) -> str:
    while path.startswith("./"):
        path = path[2:]
    return path.rstrip("/") or "."


def _root_unit(root: Path) -> Unit:
    for manifest in (PACKAGE_JSON, PYPROJECT):
        unit = _read_unit(root, ".", manifest)
        if unit:
            return unit
    raise NoUnitError(f"no unit found: no workspace, and no version in the root {PACKAGE_JSON} or {PYPROJECT}")


def _read_unit(root: Path, path: str, manifest: str) -> Unit | None:
    """The unit at `path`, or None when it has no manifest or no static version (not a unit)."""
    file = root / path / manifest
    if not file.is_file():
        return None
    if manifest == PACKAGE_JSON:
        data = _load_json(file)
    else:
        data = _load_toml(file).get("project", {})
    version, name = data.get("version"), data.get("name")
    if version is None:
        return None
    where = _rel(root, file)
    if not isinstance(version, str) or not _VERSION.fullmatch(version):
        raise ConfigError(f"{where}: version {version!r} is not a plain X.Y.Z version")
    if not isinstance(name, str) or not name:
        raise ConfigError(f"{where}: a versioned unit needs a name")
    return Unit(path=path, name=name, dir=(root / path).resolve().name, manifest=manifest, version=version)


def _manifest_version(file: Path, text: str) -> Any:
    try:
        if file.name == PACKAGE_JSON:
            return json.loads(text).get("version")
        return tomllib.loads(text).get("project", {}).get("version")
    except ValueError:
        return None


# relscribe.toml


def _load_config(root: Path) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    """The validated global settings and the per-unit settings keyed by unit path."""
    file = root / CONFIG
    if not file.is_file():
        return {}, {}
    data = _load_toml(file)
    units = data.pop("units", {})
    if not isinstance(units, dict) or not all(isinstance(t, dict) for t in units.values()):
        raise ConfigError(f'{CONFIG}: `units` must hold [units."<path>"] tables')
    defaults = _settings(data, CONFIG)
    per_unit = {_norm(path): _settings(table, f'{CONFIG} [units."{path}"]') for path, table in units.items()}
    return defaults, per_unit


def _settings(table: dict[str, Any], where: str) -> dict[str, Any]:
    out = {}
    for key, value in table.items():
        check = _CHECKS.get(key)
        if check is None:
            raise ConfigError(f"{where}: unknown key `{key}`")
        out[key] = check(value, f"{where}: `{key}`")
    return out


def _check_tag(value: Any, where: str) -> str:
    if not isinstance(value, str):
        raise ConfigError(f"{where} must be a string")
    try:
        fields = [f for _, f, _, _ in string.Formatter().parse(value) if f is not None]
    except ValueError as exc:
        raise ConfigError(f"{where}: {exc}") from None
    unknown = [f for f in fields if f not in _PLACEHOLDERS]
    if unknown:
        raise ConfigError(f"{where}: unknown placeholder {{{unknown[0]}}}; use {{name}}, {{dir}} or {{version}}")
    return value


def _check_changelog(value: Any, where: str) -> bool:
    if not isinstance(value, bool):
        raise ConfigError(f"{where} must be true or false")
    return value


def _check_exclude(value: Any, where: str) -> tuple[str, ...]:
    return tuple(_strings(value, where))


def _check_sync(value: Any, where: str) -> tuple[Sync, ...]:
    if not isinstance(value, list):
        raise ConfigError(f"{where} must be a list of {{ file, pattern }} tables")
    out = []
    for entry in value:
        if not isinstance(entry, dict) or set(entry) != {"file", "pattern"}:
            raise ConfigError(f"{where}: each entry must be exactly {{ file, pattern }}")
        file, pattern = entry["file"], entry["pattern"]
        if not isinstance(file, str) or not isinstance(pattern, str):
            raise ConfigError(f"{where}: `file` and `pattern` must be strings")
        try:
            compiled = re.compile(pattern, re.MULTILINE)
        except re.error as exc:
            raise ConfigError(f"{where}: invalid pattern {pattern!r}: {exc}") from None
        if compiled.groups != 1:
            raise ConfigError(f"{where}: pattern {pattern!r} must have exactly one capture group")
        out.append(Sync(file=file, pattern=compiled))
    return tuple(out)


def _check_bump(value: Any, where: str) -> dict[str, str]:
    if not isinstance(value, dict) or not all(v in _BUMPS for v in value.values()):
        raise ConfigError(f'{where} must map commit types to "major", "minor" or "patch"')
    return dict(value)


_CHECKS = {
    "tag": _check_tag,
    "changelog": _check_changelog,
    "exclude": _check_exclude,
    "sync": _check_sync,
    "bump": _check_bump,
}


def _with_settings(unit: Unit, settings: dict[str, Any]) -> Unit:
    # The manifest is always rewritten first, so a sync entry on it would only see the new version.
    for sync in settings.get("sync", ()):
        if _norm(sync.file) == unit.manifest:
            raise ConfigError(f"{CONFIG}: unit {unit.path}: sync must not target the manifest {unit.manifest}")
    return Unit(
        path=unit.path, name=unit.name, dir=unit.dir, manifest=unit.manifest, version=unit.version, **settings
    )


# Targeted edits: only the version's characters change, so formatting survives.

_JSON_TOKEN = re.compile(r'"(?:[^"\\]|\\.)*"|[{}\[\]:]')


def _json_version_span(text: str) -> tuple[int, int]:
    """The span of the top-level `"version"` string's contents, ignoring nested keys."""
    tokens = list(_JSON_TOKEN.finditer(text))
    depth = 0
    for i, token in enumerate(tokens):
        value = token.group()
        if value in "{[":
            depth += 1
        elif value in "}]":
            depth -= 1
        elif (
            depth == 1
            and value == '"version"'
            and i + 2 < len(tokens)
            and tokens[i + 1].group() == ":"
            and tokens[i + 2].group().startswith('"')
        ):
            return tokens[i + 2].start() + 1, tokens[i + 2].end() - 1
    raise ConfigError(f"{PACKAGE_JSON}: no top-level version")


def _toml_version_span(text: str, file: Path) -> tuple[int, int]:
    """The span of `version = "…"`'s value inside the [project] table."""
    offset = 0
    in_project = False
    for line in text.splitlines(keepends=True):
        stripped = line.strip()
        if stripped.startswith("["):
            in_project = re.match(r"\[\s*project\s*\]", stripped) is not None
        elif in_project:
            m = re.match(r"""\s*version\s*=\s*(["'])(.*?)\1""", line)
            if m:
                return offset + m.start(2), offset + m.end(2)
        offset += len(line)
    raise ConfigError(f"{file}: no `version = \"…\"` line in [project]")


# Reading files


def _read(file: Path) -> str:
    # newline="" keeps CRLF line endings intact through a rewrite.
    with file.open(encoding="utf-8", newline="") as f:
        return f.read()


def _load_json(file: Path) -> dict[str, Any]:
    try:
        data = json.loads(_read(file))
    except ValueError as exc:
        raise ConfigError(f"{file.name}: invalid JSON: {exc}") from None
    if not isinstance(data, dict):
        raise ConfigError(f"{file.name}: expected a JSON object")
    return data


def _load_toml(file: Path) -> dict[str, Any]:
    try:
        return tomllib.loads(_read(file))
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"{file.name}: invalid TOML: {exc}") from None


def _strings(value: Any, where: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
        raise ConfigError(f"{where} must be a list of strings")
    return value


def _rel(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()
