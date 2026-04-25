# Concepts

The four dimensions and the philosophy behind them.

## Fever chart, not thermometer

Every metric SDI computes is trackable over time. The primary output is the *trend* — the rate of change of structural coherence — not the absolute state. Alerts fire on rate-of-change thresholds, not absolute values, because a healthy codebase has lots of patterns and lots of boundaries, and "absolute high" tells you nothing without a "compared to what."

## Measurement over opinion

SDI never classifies code as "good" or "bad." Pattern entropy is a measurement, not a verdict. Threshold breaches are reported as "exceeded," not as "violations." When a metric moves, SDI tells you *how much* and *where*, never *whether you should be worried*. That call is yours.

## The four dimensions

### Pattern Entropy

For each pattern category (error handling, async, data access, logging, class hierarchy, context managers, comprehensions, shell-specific patterns), SDI counts distinct structural shapes. A repo with one canonical error-handling shape has low pattern entropy in that category; a repo with seven competing shapes has high pattern entropy. Drift in this dimension means "we are accumulating ways to do the same thing."

### Convention Drift Rate

The velocity vector — first derivative of pattern entropy. A spike means new shapes are arriving rapidly. Sustained high drift may be a deliberate migration (declared via `[thresholds.overrides.*]` with an expiry date) or unmanaged churn. SDI does not classify which.

### Coupling Topology Delta

The dependency graph changes shape as code evolves: new edges, new bridge nodes, articulation points moving, components merging or splitting. Coupling topology delta is the magnitude of that structural change between snapshots.

### Boundary Violation Velocity

After Leiden community detection produces inferred boundaries (which a human ratifies in `.sdi/boundaries.yaml`), SDI counts imports that cross those boundaries against declared rules. Velocity is the rate of new violations per snapshot interval.

## Snapshots and determinism

A snapshot is a JSON document captured at a specific commit. Same commit + same config + same boundaries = same snapshot, byte for byte. Determinism is enforced by:

- Seeded Leiden community detection (random seed default 42; warm starts seed from the previous partition).
- No network calls during analysis.
- No ML/LLM in the pipeline.

## Inferred boundaries vs. declared boundaries

Leiden detects communities in the import graph and proposes them as boundaries. Until a human ratifies `.sdi/boundaries.yaml`, those boundaries are inferred and SDI computes drift against them. Once ratified, SDI computes drift against the declared intent. The difference is *intent divergence* — how far the actual structure has drifted from the architecture you wanted.
