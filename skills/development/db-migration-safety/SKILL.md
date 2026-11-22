---
name: db-migration-safety
description: Reviews Postgres schema migrations for table locks, rewrites, and changes that break running code, then rewrites them safely. Use for any migration file, ALTER TABLE, index, or column change.
compatibility: Lint script requires Python 3.8+ (standard library only). Rules target PostgreSQL 11+.
---

# Detailed Instructions

A migration is safe when it neither blocks traffic nor breaks the version of the app that is still
running while it deploys. Check both, every time — a migration that passes on an empty dev database
can lock a production table for minutes.

## Overview

Most migration outages come from a short list of operations: building an index without
`CONCURRENTLY`, adding a constraint that scans the whole table under an exclusive lock, changing a
column type (full rewrite), or renaming and dropping columns the old app version still reads. This
skill lints the migration with `scripts/lint_migration.py`, explains each risk in terms of locks and
deploy order, and rewrites the migration into safe steps (expand → migrate → contract).

## Workflow Rules

1. **Find the migration** and the database (PostgreSQL version if known; framework: Rails, Django,
   Alembic, Prisma, Flyway, plain SQL). For ORM migrations, get the generated SQL first
   (`rails db:migrate:status` + `--dry-run` tools, `python manage.py sqlmigrate app 0042`,
   `alembic upgrade head --sql`, `prisma migrate diff --script`).
2. **Run the linter** on the SQL: `python3 scripts/lint_migration.py path/to/migration.sql`
   (or pipe SQL on stdin). It flags known lock and rewrite patterns with line numbers.
3. **Check table size and traffic** when possible (`SELECT pg_size_pretty(pg_total_relation_size('orders'))`).
   Risk scales with table size and write rate; a 2 KB lookup table is not a concern.
4. **Apply the safe patterns** for each finding:

   | Risky | Safe |
   |---|---|
   | `CREATE INDEX` | `CREATE INDEX CONCURRENTLY` — outside a transaction (disable the framework's wrapping transaction for that migration) |
   | `ADD CONSTRAINT … FOREIGN KEY` / `CHECK` | add with `NOT VALID`, then `VALIDATE CONSTRAINT` in a separate migration |
   | `SET NOT NULL` on a big table | add `CHECK (col IS NOT NULL) NOT VALID`, validate it, then `SET NOT NULL` (PG 12+ skips the scan), then drop the check |
   | `ADD UNIQUE` / `PRIMARY KEY` | `CREATE UNIQUE INDEX CONCURRENTLY`, then `ADD CONSTRAINT … USING INDEX` |
   | `ALTER COLUMN … TYPE` (rewrite) | add a new column, dual-write, backfill in batches, switch reads, drop the old column later |
   | `ADD COLUMN … DEFAULT <volatile>` (e.g. `gen_random_uuid()`) | add the column without a default, backfill in batches, then set the default |
   | `RENAME COLUMN` / `DROP COLUMN` / `RENAME TABLE` | expand/contract: ship code that stops using it first, drop in a later deploy |
   | Unbatched `UPDATE` / `DELETE` backfill | batches of 1–10k rows by primary key, each in its own transaction |

5. **Set a lock timeout** at the top of migrations that take `ACCESS EXCLUSIVE` locks
   (`SET lock_timeout = '5s';`) so a blocked migration fails fast instead of queuing all traffic
   behind it. Retry later rather than raising the timeout.
6. **Order the deploys**: say which steps ship before the code change, with it, and after it.
7. **Re-run the linter** on the rewritten SQL and show it is clean (or explain any accepted warning).

## Anti-Patterns (What NOT to do)

* Do not approve a migration because it ran quickly in development or CI; those tables are tiny.
* Do not put `CREATE INDEX CONCURRENTLY` inside a transaction block; Postgres rejects it.
* Do not rename or drop a column in the same deploy as the code that stops using it.
* Do not backfill millions of rows in a single `UPDATE`; it holds locks and bloats the table.
* Do not raise `lock_timeout` or `statement_timeout` to make a risky migration "work".
* Do not treat linter silence as proof of safety; it knows patterns, not your traffic.

## Examples

**User:** "Is this migration OK to run on production? `orders` has ~40M rows."

```sql
ALTER TABLE orders ADD COLUMN public_id uuid NOT NULL DEFAULT gen_random_uuid();
CREATE UNIQUE INDEX orders_public_id_idx ON orders (public_id);
ALTER TABLE orders ADD CONSTRAINT orders_customer_fk FOREIGN KEY (customer_id) REFERENCES customers (id);
ALTER TABLE orders RENAME COLUMN total TO total_cents;
```

**Expected output:**

```text
$ python3 scripts/lint_migration.py migration.sql
migration.sql:1  ERROR  volatile-default     ADD COLUMN with a volatile DEFAULT rewrites the whole table under ACCESS EXCLUSIVE
migration.sql:2  ERROR  index-not-concurrent CREATE INDEX without CONCURRENTLY blocks writes while it builds
migration.sql:3  ERROR  constraint-validates FOREIGN KEY without NOT VALID scans the table while holding locks
migration.sql:4  ERROR  breaking-rename      RENAME COLUMN breaks app instances still using the old name
migration.sql:*  WARN   no-lock-timeout      ALTER TABLE without SET lock_timeout

Not safe for a 40M-row table: line 1 alone rewrites every row while blocking reads and writes.

## Safe version — 3 migrations + code changes

-- Migration A (ship first)
SET lock_timeout = '5s';
ALTER TABLE orders ADD COLUMN public_id uuid;                 -- metadata only, instant
ALTER TABLE orders ADD COLUMN total_cents bigint;              -- new column instead of rename
ALTER TABLE orders ADD CONSTRAINT orders_customer_fk
  FOREIGN KEY (customer_id) REFERENCES customers (id) NOT VALID;
ALTER TABLE orders ALTER COLUMN public_id SET DEFAULT gen_random_uuid();  -- new rows only

-- Code deploy 1: write both total and total_cents; generate public_id in the app as a fallback.
-- Backfill job: UPDATE orders SET public_id = gen_random_uuid(), total_cents = total
--               WHERE id BETWEEN :start AND :start + 9999 AND public_id IS NULL;  (loop by id)

-- Migration B (after backfill; no transaction wrapper)
CREATE UNIQUE INDEX CONCURRENTLY orders_public_id_idx ON orders (public_id);
ALTER TABLE orders VALIDATE CONSTRAINT orders_customer_fk;     -- SHARE UPDATE EXCLUSIVE, no write block

-- Code deploy 2: read total_cents only; stop writing total.
-- Migration C (later): ALTER TABLE orders DROP COLUMN total;  -- and SET NOT NULL via the CHECK pattern

Re-lint of A and B: clean except an accepted WARN on Migration C's DROP COLUMN (ships after deploy 2).
```
