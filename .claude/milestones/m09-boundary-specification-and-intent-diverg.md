### Milestone 9: Boundary Specification and Intent Divergence

**Scope:** Implement boundary specification management — parsing `.sdi/boundaries.yaml`, the `sdi boundaries` command with `--propose`, `--ratify`, and `--export` flags, and intent divergence computation (comparing detected Leiden partitions against ratified boundary specs). Extend `sdi init` to optionally propose and write a starter boundary spec.

**Deliverables:**
- `src/sdi/detection/boundaries.py` with `BoundarySpec` dataclass, YAML parsing via ruamel.yaml (comment-preserving), validation of required fields, intent divergence computation (files in wrong boundary, unexpected cross-boundary dependencies, layer direction violations)
- `src/sdi/cli/boundaries_cmd.py` with `--propose` (run Leiden and show proposed boundaries), `--ratify` (open in `$EDITOR`), `--export` (write to file), display modes (text/yaml)
- Update `src/sdi/cli/init_cmd.py` to optionally run inference and write starter `boundaries.yaml`
- Update `src/sdi/snapshot/assembly.py` to include intent divergence metrics in snapshots when a boundary spec exists
- Update `src/sdi/snapshot/delta.py` to include intent divergence changes in boundary violation velocity
- `tests/unit/test_boundaries.py`

**Acceptance criteria:**
- `BoundarySpec` correctly parses the YAML schema (modules, layers, allowed_cross_domain, aspirational_splits)
- Malformed boundary YAML exits with code 2 and descriptive error including line number
- Missing boundary spec is normal operation — no warning, no degraded mode, intent divergence metrics simply omitted from snapshot
- `sdi boundaries` displays the current ratified boundary map
- `sdi boundaries --propose` runs Leiden inference and displays proposed boundaries as a diff against the current spec
- `sdi boundaries --ratify` opens the boundary spec in `$EDITOR` for editing
- `sdi boundaries --export /tmp/boundaries.yaml` writes the current boundary map
- Intent divergence computation identifies: files assigned to wrong boundary (compared to spec), cross-boundary imports not in `allowed_cross_domain`, layer direction violations (e.g., domain importing from presentation)
- `allowed_cross_domain` entries suppress specific cross-boundary dependency flags
- `aspirational_splits` are tracked but do not affect current metrics
- ruamel.yaml preserves comments on round-trip when `--ratify` writes back
- `pytest tests/unit/test_boundaries.py` passes

**Tests:**
- `tests/unit/test_boundaries.py`: Parse valid boundary spec, reject spec with missing required fields, handle missing spec file gracefully (returns None, not error), intent divergence identifies misplaced files, intent divergence identifies unauthorized cross-boundary imports, intent divergence respects allowed_cross_domain exceptions, layer direction validation (downward = presentation → domain → infrastructure is OK, reverse is a violation), aspirational splits parsed and included in output, ruamel.yaml comment preservation verified on write-read cycle

**Watch For:**
- ruamel.yaml API differs from PyYAML — use `YAML(typ='rt')` (round-trip) for comment preservation
- `--ratify` opens `$EDITOR` — handle the case where `$EDITOR` is not set (fall back to `vi` on Unix, warn on Windows)
- Intent divergence computation must handle the case where the Leiden partition has different boundaries than the spec — this is expected (detection vs. ratified intent) and the difference is the measurement
- Layer direction validation: "downward" means a module in an upper layer may depend on a module in a lower layer, but not the reverse. The `layers.ordering` list defines the order from top to bottom.

**Seeds Forward:**
- Intent divergence metrics feed into `boundary_violation_velocity` in the snapshot delta — they add to (not replace) the partition-based boundary violation count
- The boundary spec `version` field enables schema evolution for boundary specs in future versions
- `aspirational_splits` could feed into a progress-toward-separation metric in post-v1

---
