# typescript-realistic fixture

Synthetic TypeScript fixture simulating a small backend service with the
structure observed in bifl-tracker. Used by
`tests/integration/test_validation_typescript_realistic.py` to assert that
M15 alias-resolution, M16 per-language entropy, and the TS adapter produce
correct signal on a realistic TypeScript codebase.

## Structure

```
src/
  index.ts          — entrypoint; imports all api handlers
  config.ts         — environment config (leaf)
  types.ts          — domain types and runtime constants
  api/
    users.ts        — user CRUD handlers
    orders.ts       — order handlers
    products.ts     — product listing handlers
    auth.ts         — login / token verification
    health.ts       — health + readiness endpoints
  db/
    models/
      user.ts       — User row model
      order.ts      — Order row model
      product.ts    — Product row model
    queries.ts      — SQL query functions
  lib/
    logger.ts       — structured logging
    errors.ts       — AppError hierarchy (leaf)
    validate.ts     — input validation utilities
    cache.ts        — in-memory cache utilities
```

**Total TypeScript files: 16** (within the 15–25 range asserted by the test).

## tsconfig.json Path Aliases

The fixture includes a `tsconfig.json` with:

```json
"paths": { "@/*": ["./src/*"] }
```

This exercises the M15 alias resolver. All intra-project imports use `@/`
prefixes (e.g., `@/lib/logger`, `@/db/queries`).

## Import Edge Count (manually counted)

| File | Value imports | Target(s) |
|---|---|---|
| src/index.ts | 8 | api/* (5), lib/logger, config, types |
| src/api/users.ts | 3 | db/queries, lib/logger, lib/validate |
| src/api/orders.ts | 3 | db/queries, lib/logger, lib/errors |
| src/api/products.ts | 2 | db/queries, lib/logger |
| src/api/auth.ts | 4 | db/queries, lib/logger, lib/validate, lib/errors |
| src/api/health.ts | 1 | lib/logger |
| src/db/queries.ts | 3 | db/models/user, db/models/order, db/models/product |
| src/lib/logger.ts | 1 | config |
| src/lib/validate.ts | 1 | lib/errors |
| src/lib/cache.ts | 1 | config |

Note: `import type { ... }` imports are type-only and do not generate graph
edges (the TS adapter excludes them per the SDI architecture).

**Total import edges: 27** (within the 20–40 range; test asserts `>= 20`).

## Connectivity

All 16 files are weakly connected through `src/index.ts` (component_count == 1).
Leiden community detection should produce at least 2 clusters corresponding
to the api, db, and lib layers.

## Pattern Shape Distribution

| Category | Distinct shapes | Example constructs |
|---|---|---|
| error_handling | ≥ 3 | try/catch, try/catch/finally, try with rethrow |
| logging | ≥ 2 | console.log (different arg structures), console.error |

**Sum ≥ 5** — satisfies `pattern_entropy_by_language["typescript"] >= 5`.

## Updating the Fixture

If you add or remove import statements, update the edge count table above
and adjust the test assertion floor in `test_validation_typescript_realistic.py`
accordingly.
