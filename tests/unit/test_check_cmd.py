"""Unit tests for the check command threshold logic.

Tests run_checks() and _effective_threshold() in isolation from the CLI.
"""

from __future__ import annotations

from sdi.cli.check_cmd import CheckResult, run_checks
from sdi.config import SDIConfig, ThresholdOverride, ThresholdsConfig
from sdi.snapshot.model import DivergenceSummary


def _config(
    pattern_entropy_rate: float = 2.0,
    convention_drift_rate: float = 0.10,
    coupling_delta_rate: float = 0.15,
    boundary_violation_rate: float = 5.0,
    overrides: dict | None = None,
) -> SDIConfig:
    """Build a minimal SDIConfig for threshold testing."""
    config = SDIConfig()
    config.thresholds = ThresholdsConfig(
        pattern_entropy_rate=pattern_entropy_rate,
        convention_drift_rate=convention_drift_rate,
        coupling_delta_rate=coupling_delta_rate,
        boundary_violation_rate=boundary_violation_rate,
        overrides=overrides or {},
    )
    return config


def _div(
    pe_delta: float | None = None,
    cd_delta: float | None = None,
    ct_delta: float | None = None,
    bv_delta: int | None = None,
) -> DivergenceSummary:
    """Build a DivergenceSummary with specified delta values."""
    return DivergenceSummary(
        pattern_entropy=1.0,
        pattern_entropy_delta=pe_delta,
        convention_drift=0.1,
        convention_drift_delta=cd_delta,
        coupling_topology=0.2,
        coupling_topology_delta=ct_delta,
        boundary_violations=0,
        boundary_violations_delta=bv_delta,
    )


class TestRunChecksNullDeltas:
    """Null deltas (first snapshot) must not trigger a breach."""

    def test_all_null_deltas_no_breach(self) -> None:
        div = _div()  # all deltas None
        results = run_checks(div, _config())
        assert all(not r.exceeded for r in results)

    def test_null_delta_not_exceeded_even_for_very_low_threshold(self) -> None:
        config = _config(pattern_entropy_rate=0.0)
        div = _div(pe_delta=None)
        results = run_checks(div, config)
        pe_result = next(r for r in results if r.dimension == "pattern_entropy_delta")
        assert not pe_result.exceeded


class TestRunChecksThresholds:
    """Values at and above thresholds trigger breaches correctly."""

    def test_value_below_threshold_ok(self) -> None:
        config = _config(pattern_entropy_rate=2.0)
        div = _div(pe_delta=1.9)
        results = run_checks(div, config)
        pe = next(r for r in results if r.dimension == "pattern_entropy_delta")
        assert not pe.exceeded

    def test_value_equal_to_threshold_ok(self) -> None:
        config = _config(pattern_entropy_rate=2.0)
        div = _div(pe_delta=2.0)
        results = run_checks(div, config)
        pe = next(r for r in results if r.dimension == "pattern_entropy_delta")
        # Equal to threshold is not exceeded (must be strictly greater)
        assert not pe.exceeded

    def test_value_above_threshold_exceeded(self) -> None:
        config = _config(pattern_entropy_rate=2.0)
        div = _div(pe_delta=2.1)
        results = run_checks(div, config)
        pe = next(r for r in results if r.dimension == "pattern_entropy_delta")
        assert pe.exceeded

    def test_negative_delta_never_exceeded(self) -> None:
        """Negative deltas (improving metrics) must never trigger a breach."""
        config = _config(pattern_entropy_rate=2.0)
        div = _div(pe_delta=-5.0)
        results = run_checks(div, config)
        pe = next(r for r in results if r.dimension == "pattern_entropy_delta")
        assert not pe.exceeded

    def test_all_four_dimensions_checked(self) -> None:
        results = run_checks(_div(), _config())
        dims = {r.dimension for r in results}
        assert dims == {
            "pattern_entropy_delta",
            "convention_drift_delta",
            "coupling_topology_delta",
            "boundary_violations_delta",
        }


class TestRunChecksOverrides:
    """Active threshold overrides relax thresholds; expired ones do not."""

    def test_active_override_raises_threshold(self) -> None:
        override = ThresholdOverride(
            expires="2099-12-31",
            pattern_entropy_rate=10.0,
        )
        config = _config(pattern_entropy_rate=2.0, overrides={"migration": override})
        # Delta of 5.0 would normally breach 2.0 but override allows 10.0
        div = _div(pe_delta=5.0)
        results = run_checks(div, config)
        pe = next(r for r in results if r.dimension == "pattern_entropy_delta")
        assert not pe.exceeded

    def test_override_does_not_lower_threshold(self) -> None:
        """An override that is lower than base should not tighten the threshold."""
        override = ThresholdOverride(
            expires="2099-12-31",
            pattern_entropy_rate=0.5,
        )
        config = _config(pattern_entropy_rate=2.0, overrides={"low": override})
        # Delta of 1.9 should still be within the base threshold of 2.0
        div = _div(pe_delta=1.9)
        results = run_checks(div, config)
        pe = next(r for r in results if r.dimension == "pattern_entropy_delta")
        assert not pe.exceeded

    def test_multiple_overrides_highest_wins(self) -> None:
        overrides = {
            "a": ThresholdOverride(expires="2099-12-31", pattern_entropy_rate=5.0),
            "b": ThresholdOverride(expires="2099-12-31", pattern_entropy_rate=8.0),
        }
        config = _config(pattern_entropy_rate=2.0, overrides=overrides)
        div = _div(pe_delta=7.5)  # Between 5.0 and 8.0
        results = run_checks(div, config)
        pe = next(r for r in results if r.dimension == "pattern_entropy_delta")
        assert not pe.exceeded  # Highest override (8.0) applies

    def test_override_only_affects_specified_dimensions(self) -> None:
        """Override for pattern_entropy should not affect convention_drift threshold."""
        override = ThresholdOverride(
            expires="2099-12-31",
            pattern_entropy_rate=100.0,
        )
        config = _config(convention_drift_rate=3.0, overrides={"migration": override})
        div = _div(cd_delta=4.0)  # Exceeds convention_drift_rate=3.0
        results = run_checks(div, config)
        cd = next(r for r in results if r.dimension == "convention_drift_delta")
        assert cd.exceeded

    def test_expired_override_does_not_raise_threshold(self) -> None:
        """An expired override must not relax the base threshold (CLAUDE.md rule 5).

        Expiry filtering happens at config-load time via _build_overrides().
        This test verifies the end-to-end contract: an override with a past
        expiry date is silently dropped and the base threshold applies.
        """
        from sdi.config import _build_overrides

        # Build overrides through the real config layer — expired in the past
        overrides = _build_overrides(
            {
                "old_migration": {
                    "expires": "2020-01-01",
                    "pattern_entropy_rate": 100.0,  # Would relax to 100.0 if applied
                }
            }
        )
        # The config layer must have silently dropped the expired entry
        assert "old_migration" not in overrides

        # Verify run_checks uses the base threshold (2.0), not the expired one (100.0)
        config = _config(pattern_entropy_rate=2.0, overrides=overrides)
        div = _div(pe_delta=5.0)  # 5.0 > 2.0 (base) but < 100.0 (expired override)
        results = run_checks(div, config)
        pe = next(r for r in results if r.dimension == "pattern_entropy_delta")
        assert pe.exceeded  # Base threshold applies; expired override is absent


class TestCheckResult:
    """CheckResult serialization."""

    def test_to_dict_ok(self) -> None:
        result = CheckResult("pattern_entropy_delta", 1.5, 2.0, exceeded=False)
        d = result.to_dict()
        assert d["status"] == "ok"
        assert d["value"] == 1.5
        assert d["threshold"] == 2.0

    def test_to_dict_exceeded(self) -> None:
        result = CheckResult("pattern_entropy_delta", 3.0, 2.0, exceeded=True)
        d = result.to_dict()
        assert d["status"] == "exceeded"

    def test_to_dict_null_value(self) -> None:
        result = CheckResult("pattern_entropy_delta", None, 2.0, exceeded=False)
        d = result.to_dict()
        assert d["value"] is None
        assert d["status"] == "ok"
