"""Unit tests for M16 per-language delta helpers and compute_delta extensions."""

from __future__ import annotations

import warnings

import pytest

from sdi.snapshot._lang_delta import per_language_convention_drift, per_language_pattern_entropy
from sdi.snapshot.delta import compute_delta
from sdi.snapshot.model import DivergenceSummary
from tests.unit._delta_helpers import (
    OLD_SCHEMA_VERSION as _OLD_SCHEMA_VERSION,
)
from tests.unit._delta_helpers import (
    catalog as _catalog,
)
from tests.unit._delta_helpers import (
    catalog_with_files as _catalog_with_files,
)
from tests.unit._delta_helpers import (
    fake_record as _fake_record,
)
from tests.unit._delta_helpers import (
    make_snap as _make_snap,
)

# ---------------------------------------------------------------------------
# per_language_pattern_entropy
# ---------------------------------------------------------------------------


class TestPerLanguagePatternEntropy:
    """per_language_pattern_entropy returns distinct shape count per language."""

    def test_python_and_shell_two_keys(self) -> None:
        cat = _catalog_with_files({"error_handling": [("h_py", "a.py", 1), ("h_sh", "b.sh", 1)]})
        file_lang = {"a.py": "python", "b.sh": "shell"}
        result = per_language_pattern_entropy(cat, file_lang)
        assert "python" in result and "shell" in result

    def test_python_entropy_counts_python_shapes(self) -> None:
        cat = _catalog_with_files({"error_handling": [("h_py", "a.py", 1), ("h_sh", "b.sh", 1)]})
        file_lang = {"a.py": "python", "b.sh": "shell"}
        result = per_language_pattern_entropy(cat, file_lang)
        assert result["python"] == 1.0
        assert result["shell"] == 1.0

    def test_python_only_categories_not_counted_for_shell(self) -> None:
        """class_hierarchy does not count for shell."""
        cat = _catalog_with_files(
            {
                "class_hierarchy": [("ch1", "a.py", 1)],
                "error_handling": [("eh1", "b.sh", 1)],
            }
        )
        file_lang = {"a.py": "python", "b.sh": "shell"}
        result = per_language_pattern_entropy(cat, file_lang)
        assert result["shell"] == 1.0  # only error_handling applicable
        assert result["python"] == 1.0  # class_hierarchy with python file

    def test_empty_catalog_returns_empty(self) -> None:
        assert per_language_pattern_entropy({}, {"a.py": "python"}) == {}

    def test_empty_file_lang_map_returns_empty(self) -> None:
        assert per_language_pattern_entropy(_catalog({"error_handling": ["h1"]}), {}) == {}

    def test_output_is_deterministically_sorted(self) -> None:
        cat = _catalog_with_files({"error_handling": [("h1", "a.py", 1), ("h2", "b.sh", 1)]})
        file_lang = {"a.py": "python", "b.sh": "shell"}
        result = per_language_pattern_entropy(cat, file_lang)
        assert list(result.keys()) == sorted(result.keys())


# ---------------------------------------------------------------------------
# per_language_convention_drift
# ---------------------------------------------------------------------------


class TestPerLanguageConventionDrift:
    """per_language_convention_drift uses per-language canonicals."""

    def test_two_languages_two_keys(self) -> None:
        cat = _catalog_with_files(
            {
                "error_handling": [
                    ("h_py_canon", "a.py", 2),
                    ("h_py_non", "b.py", 1),
                    ("h_sh_canon", "c.sh", 3),
                ],
            }
        )
        file_lang = {"a.py": "python", "b.py": "python", "c.sh": "shell"}
        result = per_language_convention_drift(cat, file_lang)
        assert "python" in result and "shell" in result

    def test_python_drift_uses_python_canonical(self) -> None:
        """Python canonical differs from shell canonical — graded independently."""
        cat = _catalog_with_files(
            {
                "error_handling": [
                    ("h_py_canon", "a.py", 2),
                    ("h_py_non", "b.py", 1),
                    ("h_sh", "c.sh", 5),
                ],
            }
        )
        file_lang = {"a.py": "python", "b.py": "python", "c.sh": "shell"}
        result = per_language_convention_drift(cat, file_lang)
        assert result["python"] == pytest.approx(1 / 2)
        assert result["shell"] == pytest.approx(0.0)

    def test_zero_drift_when_one_shape(self) -> None:
        cat = _catalog_with_files({"error_handling": [("h1", "a.py", 3)]})
        result = per_language_convention_drift(cat, {"a.py": "python"})
        assert result["python"] == pytest.approx(0.0)

    def test_python_only_category_excluded_for_shell(self) -> None:
        """class_hierarchy shapes don't contribute to shell drift."""
        cat = _catalog_with_files(
            {
                "class_hierarchy": [("ch1", "a.py", 1), ("ch2", "a.py", 1)],
                "error_handling": [("eh1", "b.sh", 2), ("eh2", "b.sh", 1)],
            }
        )
        file_lang = {"a.py": "python", "b.sh": "shell"}
        result = per_language_convention_drift(cat, file_lang)
        assert result["shell"] == pytest.approx(1 / 2)

    def test_empty_catalog_returns_empty(self) -> None:
        assert per_language_convention_drift({}, {"a.py": "python"}) == {}


# ---------------------------------------------------------------------------
# compute_delta with per-language fields
# ---------------------------------------------------------------------------


class TestComputeDeltaPerLanguage:
    """compute_delta populates per-language fields on new snapshots."""

    def test_first_snapshot_per_language_deltas_are_none(self) -> None:
        snap = _make_snap(
            pattern_catalog=_catalog_with_files({"error_handling": [("h1", "a.py", 1)]}),
            feature_records=[_fake_record("a.py", "python")],
        )
        result = compute_delta(snap, None)
        assert result.pattern_entropy_by_language_delta is None
        assert result.convention_drift_by_language_delta is None

    def test_first_snapshot_absolute_per_language_populated(self) -> None:
        snap = _make_snap(
            pattern_catalog=_catalog_with_files({"error_handling": [("h1", "a.py", 1)]}),
            feature_records=[_fake_record("a.py", "python")],
        )
        result = compute_delta(snap, None)
        assert result.pattern_entropy_by_language is not None
        assert "python" in result.pattern_entropy_by_language

    def test_delta_against_0_1_0_snapshot_warns_once(self) -> None:
        old_snap = _make_snap(version=_OLD_SCHEMA_VERSION)
        curr = _make_snap(
            pattern_catalog=_catalog({"error_handling": ["h1"]}),
            feature_records=[_fake_record("a.py", "python")],
        )
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            result = compute_delta(curr, old_snap)
        per_lang_warns = [w for w in caught if "0.1.0" in str(w.message) or "per-language" in str(w.message).lower()]
        assert len(per_lang_warns) == 1
        assert issubclass(per_lang_warns[0].category, UserWarning)
        assert result.pattern_entropy_by_language_delta is None

    def test_delta_against_0_1_0_aggregate_still_computed(self) -> None:
        old_snap = _make_snap(
            version=_OLD_SCHEMA_VERSION,
            pattern_catalog=_catalog({"error_handling": ["h1"]}),
        )
        curr = _make_snap(
            pattern_catalog=_catalog({"error_handling": ["h1", "h2"]}),
            feature_records=[_fake_record("a.py", "python")],
        )
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            result = compute_delta(curr, old_snap)
        assert result.pattern_entropy_delta == pytest.approx(1.0)

    def test_delta_with_new_language_added(self) -> None:
        """A language in current but not in previous has previous value treated as 0."""
        prev_snap = _make_snap(
            pattern_catalog=_catalog_with_files({"error_handling": [("h1", "a.py", 1)]}),
            feature_records=[_fake_record("a.py", "python")],
            divergence=DivergenceSummary(pattern_entropy_by_language={"python": 1.0}),
        )
        curr = _make_snap(
            pattern_catalog=_catalog_with_files({"error_handling": [("h1", "a.py", 1), ("h_sh", "b.sh", 1)]}),
            feature_records=[_fake_record("a.py", "python"), _fake_record("b.sh", "shell")],
        )
        result = compute_delta(curr, prev_snap)
        assert result.pattern_entropy_by_language_delta is not None
        assert "python" in result.pattern_entropy_by_language_delta
        assert "shell" in result.pattern_entropy_by_language_delta
        assert result.pattern_entropy_by_language_delta["shell"] > 0
