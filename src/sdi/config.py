"""Configuration loading with five-level precedence.

Precedence (highest to lowest):
    1. CLI flags (applied by callers after load_config returns)
    2. Environment variables
    3. Project-local config (.sdi/config.toml)
    4. Global user config (~/.config/sdi/config.toml)
    5. Built-in defaults
"""

from __future__ import annotations

import os
import sys
import warnings
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

try:
    import tomllib
except ImportError:
    import tomli as tomllib  # type: ignore[no-redef]


_DEFAULT_EXCLUDE = (
    "**/vendor/**",
    "**/node_modules/**",
    "**/__pycache__/**",
    "**/dist/**",
    "**/build/**",
    "**/.git/**",
)


@dataclass
class CoreConfig:
    """Core analysis settings."""

    languages: str = "auto"
    exclude: list[str] = field(default_factory=lambda: list(_DEFAULT_EXCLUDE))
    random_seed: int = 42
    log_level: str = "WARNING"
    workers: int = 0  # 0 = auto-detect CPU count


@dataclass
class SnapshotsConfig:
    """Snapshot storage settings."""

    dir: str = ".sdi/snapshots"
    retention: int = 100


@dataclass
class BoundariesConfig:
    """Leiden community detection and boundary settings."""

    spec_file: str = ".sdi/boundaries.yaml"
    leiden_gamma: float = 1.0
    stability_threshold: int = 3
    weighted_edges: bool = False


@dataclass
class PatternsConfig:
    """Pattern fingerprinting settings."""

    categories: str = "auto"
    min_pattern_nodes: int = 5


@dataclass
class ThresholdOverride:
    """Per-category threshold override with mandatory expiry."""

    expires: str
    reason: str = ""
    pattern_entropy_rate: float | None = None
    convention_drift_rate: float | None = None
    coupling_delta_rate: float | None = None
    boundary_violation_rate: float | None = None


@dataclass
class ThresholdsConfig:
    """Alert threshold configuration."""

    pattern_entropy_rate: float = 2.0
    convention_drift_rate: float = 3.0
    coupling_delta_rate: float = 0.15
    boundary_violation_rate: float = 2.0
    overrides: dict[str, ThresholdOverride] = field(default_factory=dict)


@dataclass
class ChangeCouplingConfig:
    """Change coupling analysis settings."""

    min_frequency: float = 0.6
    history_depth: int = 500


@dataclass
class OutputConfig:
    """Output formatting settings."""

    format: str = "text"
    color: str = "auto"


@dataclass
class SDIConfig:
    """Complete SDI configuration resolved from all precedence levels."""

    core: CoreConfig = field(default_factory=CoreConfig)
    snapshots: SnapshotsConfig = field(default_factory=SnapshotsConfig)
    boundaries: BoundariesConfig = field(default_factory=BoundariesConfig)
    patterns: PatternsConfig = field(default_factory=PatternsConfig)
    thresholds: ThresholdsConfig = field(default_factory=ThresholdsConfig)
    change_coupling: ChangeCouplingConfig = field(default_factory=ChangeCouplingConfig)
    output: OutputConfig = field(default_factory=OutputConfig)


_KNOWN_SECTIONS = frozenset({"core", "snapshots", "boundaries", "patterns", "thresholds", "change_coupling", "output"})


def _load_toml(path: Path) -> dict:
    """Parse a TOML file; returns {} if absent; exits with code 2 on parse error."""
    if not path.exists():
        return {}
    try:
        with open(path, "rb") as fh:
            return tomllib.load(fh)
    except tomllib.TOMLDecodeError as exc:
        print(f"[config error] {path}: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc


def _deep_merge(base: dict, override: dict) -> dict:
    """Deep-merge two dicts; override values take precedence."""
    result = dict(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _apply_env_vars(data: dict) -> dict:
    """Apply SDI_* environment variable overrides."""
    data = dict(data)
    env = os.environ
    if "SDI_LOG_LEVEL" in env:
        data.setdefault("core", {})["log_level"] = env["SDI_LOG_LEVEL"]
    if "SDI_WORKERS" in env:
        try:
            data.setdefault("core", {})["workers"] = int(env["SDI_WORKERS"])
        except ValueError:
            print(
                f"[config warning] SDI_WORKERS={env['SDI_WORKERS']!r} is not an integer; ignored.",
                file=sys.stderr,
            )
    if "SDI_SNAPSHOT_DIR" in env:
        data.setdefault("snapshots", {})["dir"] = env["SDI_SNAPSHOT_DIR"]
    if env.get("NO_COLOR"):
        data.setdefault("output", {})["color"] = "never"
    return data


def _validate_overrides(overrides: dict) -> None:
    """Require every threshold override to have a valid 'expires' key in ISO format."""
    for name, entry in overrides.items():
        if "expires" not in entry:
            print(
                f"[config error] [thresholds.overrides.{name}] is missing required 'expires' field",
                file=sys.stderr,
            )
            raise SystemExit(2)
        try:
            date.fromisoformat(entry["expires"])
        except ValueError:
            print(
                f"[config error] [thresholds.overrides.{name}] 'expires' value "
                f"{entry['expires']!r} is not a valid ISO date (expected YYYY-MM-DD)",
                file=sys.stderr,
            )
            raise SystemExit(2)


def _build_overrides(overrides: dict) -> dict[str, ThresholdOverride]:
    """Build ThresholdOverride objects, silently skipping expired entries."""
    today = date.today()
    result: dict[str, ThresholdOverride] = {}
    for name, entry in overrides.items():
        expires = date.fromisoformat(entry["expires"])
        if expires < today:
            continue  # silently ignore expired overrides
        result[name] = ThresholdOverride(
            expires=entry["expires"],
            reason=entry.get("reason", ""),
            pattern_entropy_rate=entry.get("pattern_entropy_rate"),
            convention_drift_rate=entry.get("convention_drift_rate"),
            coupling_delta_rate=entry.get("coupling_delta_rate"),
            boundary_violation_rate=entry.get("boundary_violation_rate"),
        )
    return result


def _warn_unknown_keys(data: dict) -> None:
    """Emit DeprecationWarning for unrecognized top-level config keys."""
    for key in data:
        if key not in _KNOWN_SECTIONS:
            warnings.warn(
                f"[config] Unknown configuration key '{key}' — it may have been removed or renamed.",
                DeprecationWarning,
                stacklevel=4,
            )


def _dict_to_config(data: dict) -> SDIConfig:
    """Construct SDIConfig from a fully merged dict."""
    core = data.get("core", {})
    snaps = data.get("snapshots", {})
    bounds = data.get("boundaries", {})
    pats = data.get("patterns", {})
    thresh = data.get("thresholds", {})
    cc = data.get("change_coupling", {})
    out = data.get("output", {})

    overrides_raw = thresh.get("overrides", {})
    _validate_overrides(overrides_raw)
    overrides = _build_overrides(overrides_raw)

    return SDIConfig(
        core=CoreConfig(
            languages=core.get("languages", "auto"),
            exclude=core.get("exclude", list(_DEFAULT_EXCLUDE)),
            random_seed=core.get("random_seed", 42),
            log_level=core.get("log_level", "WARNING"),
            workers=core.get("workers", 0),
        ),
        snapshots=SnapshotsConfig(
            dir=snaps.get("dir", ".sdi/snapshots"),
            retention=snaps.get("retention", 100),
        ),
        boundaries=BoundariesConfig(
            spec_file=bounds.get("spec_file", ".sdi/boundaries.yaml"),
            leiden_gamma=bounds.get("leiden_gamma", 1.0),
            stability_threshold=bounds.get("stability_threshold", 3),
            weighted_edges=bounds.get("weighted_edges", False),
        ),
        patterns=PatternsConfig(
            categories=pats.get("categories", "auto"),
            min_pattern_nodes=pats.get("min_pattern_nodes", 5),
        ),
        thresholds=ThresholdsConfig(
            pattern_entropy_rate=thresh.get("pattern_entropy_rate", 2.0),
            convention_drift_rate=thresh.get("convention_drift_rate", 3.0),
            coupling_delta_rate=thresh.get("coupling_delta_rate", 0.15),
            boundary_violation_rate=thresh.get("boundary_violation_rate", 2.0),
            overrides=overrides,
        ),
        change_coupling=ChangeCouplingConfig(
            min_frequency=cc.get("min_frequency", 0.6),
            history_depth=cc.get("history_depth", 500),
        ),
        output=OutputConfig(
            format=out.get("format", "text"),
            color=out.get("color", "auto"),
        ),
    )


def load_config(
    project_dir: Path | None = None,
    config_path: Path | None = None,
) -> SDIConfig:
    """Load configuration with five-level precedence.

    Args:
        project_dir: Repository root. Defaults to cwd.
        config_path: Explicit config file path (overrides SDI_CONFIG_PATH env var
            and the default .sdi/config.toml location).

    Returns:
        Fully resolved SDIConfig.
    """
    if project_dir is None:
        project_dir = Path.cwd()

    # SDI_CONFIG_PATH env var overrides default location (but not explicit arg)
    if config_path is None and "SDI_CONFIG_PATH" in os.environ:
        config_path = Path(os.environ["SDI_CONFIG_PATH"])

    global_cfg = _load_toml(Path.home() / ".config" / "sdi" / "config.toml")
    project_cfg = _load_toml(config_path if config_path is not None else project_dir / ".sdi" / "config.toml")

    merged = _deep_merge(global_cfg, project_cfg)
    merged = _apply_env_vars(merged)
    _warn_unknown_keys(merged)
    return _dict_to_config(merged)
