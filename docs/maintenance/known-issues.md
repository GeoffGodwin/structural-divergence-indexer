# Known Issues

A standing list of known issues that affect SDI's behavior or its CI pipeline. Each entry names the issue, where it surfaces, and the milestone or patch that's expected to resolve it.

## M14 evolving-shell test progression mismatch

**Where:** `tests/integration/test_shell_evolving.py` (full module)
**Status:** Module-level `pytest.mark.xfail` until resolved.
**Symptom:** The fixture's C2→C3 commit is documented as a "consolidation" step that should reduce error_handling pattern entropy by at least 1. Empirically, entropy stays flat (4 → 4). Several downstream multi-step tests (TestC3ToC4Regression, TestTrendSignSequence, TestCheckExitCodes) inherit this mismatch.
**Root cause (suspected):** Either the shell-pattern detection logic counts shapes differently than the M14 fixture intent, or the fixture script content does not actually consolidate the way the C3 commit message implies.
**Resolution path:** Fix to land in a `0.14.x` patch series after `v0.14.0` ships. Either the fixture content needs to actually change shape count by -1 at C3, or detection needs to recognize the consolidation. Investigation requires comparing per-script AST hashes between C2 and C3.
**How to remove the xfail:** Once entropy correctly drops at C3, delete the `pytestmark = pytest.mark.xfail(...)` block at the top of `test_shell_evolving.py` and run the suite. All tests should pass with no further changes needed.

---

This page is updated as known issues are discovered and resolved. For the active list of milestones in flight, see [Milestones](../milestones.md).
