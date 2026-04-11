# Architecture Decision Log

Accepted Architecture Change Proposals are recorded here for institutional memory.
Each entry captures why a structural change was made, preventing future developers
(or agents) from reverting to the old approach without understanding the context.

## ADL-1: Type-only import annotation convention (`type:` prefix) (Task: "M03")
- **Date**: 2026-04-10
- **Rationale**: Backward-compatible string prefix on an existing `list[str]` field; cleanly isolated to the TypeScript adapter with no impact on other languages. M4 graph builder can strip the prefix when building ed
- **Source**: Accepted ACP from pipeline run

## ADL-2: External mod declaration as relative import (`./foo`) (Task: "M03")
- **Date**: 2026-04-10
- **Rationale**: `./` prefix unambiguously distinguishes implicit file dependencies from package paths; inline `mod { }` blocks are correctly excluded. Convention is self-documenting and backward-compatible.
- **Source**: Accepted ACP from pipeline run
