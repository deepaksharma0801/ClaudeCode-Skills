---
name: db-migration-safety
description: Reviews Postgres schema migrations for table locks, rewrites, and changes that break running code, then rewrites them safely. Use for any migration file, ALTER TABLE, index, or column change.
compatibility: Lint script requires Python 3.8+ (standard library only). Rules target PostgreSQL 11+.
---

# Detailed Instructions

A migration is safe when it neither blocks traffic nor breaks the version of the app that is still
running while it deploys. Check both, every time. A migration that finishes instantly on an empty
dev database can hold a lock on a production table for minutes, and a rename that's correct in the
new code breaks every old instance still serving requests during the rollout.

## When to Use

- Any new migration file (Rails, Django, Alembic, Prisma, Flyway, Liquibase, plain SQL)
- `ALTER TABLE`, `CREATE INDEX`, constraints, column renames or type changes, drops
- Backfills and data migrations (`UPDATE`/`DELETE` over many rows)
- "Can I run this on prod?" or a migration that caused an incident

**Don't use when:** the database is MySQL (lock behavior differs — use online DDL
`ALGORITHM=INSTANT/INPLACE` or gh-ost/pt-online-schema-change, and say the linter rules target
Postgres), or the change is to data in a table nobody reads concurrently (e.g. a brand-new table).

## Overview

Most migration outages come from a short list of operations: building an index without
`CONCURRENTLY`, adding a constraint that scans the whole table under an exclusive lock, changing a
column type (full rewrite), adding a column with a volatile default, or renaming and dropping
columns the old app version still reads. This skill lints the migration with
`scripts/lint_migration.py`, checks table size, explains each risk in terms of locks and deploy
order, and rewrites the migration into safe steps (expand → migrate → contract). Lock details per
statement and framework settings are in `references/postgres-locks.md`.

## Workflow Rules

### 1. Get the real SQL

1. **Identify the database and tool:** PostgreSQL version if known; Rails, Django, Alembic, Prisma,
   Flyway, or plain SQL. ORMs hide the statements, so get the generated SQL first:
   `python manage.py sqlmigrate app 0042`, `alembic upgrade head --sql`,
   `prisma migrate diff --from-… --to-… --script`, or read the Rails migration's DSL (and use the
   `strong_migrations` gem if it's installed).
2. **Run the linter:** `python3 scripts/lint_migration.py path/to/migration.sql` (or pipe SQL on
   stdin). It flags known lock, rewrite, and compatibility patterns with line numbers and exits
   non-zero on errors.

### 2. Judge the real risk

3. **Check size and traffic** of each table touched:
   `SELECT pg_size_pretty(pg_total_relation_size('orders')), (SELECT reltuples::bigint FROM pg_class WHERE relname = 'orders');`
   Risk scales with rows and write rate. A 2 KB lookup table is not a concern; a 40M-row orders
   table under constant writes is.
4. **Know what each lock blocks.** Read `references/postgres-locks.md` when unsure: which
   statements block reads, which block writes, and which rewrite or scan the table.

### 3. Rewrite it safely

5. **Apply the safe pattern for each finding:**

   | Risky | Safe |
   |---|---|
   | `CREATE INDEX` | `CREATE INDEX CONCURRENTLY` — in its own migration, outside a transaction |
   | `ADD CONSTRAINT … FOREIGN KEY` / `CHECK` | add with `NOT VALID`, then `VALIDATE CONSTRAINT` in a separate migration |
   | `SET NOT NULL` on a big table | add `CHECK (col IS NOT NULL) NOT VALID`, validate it, then `SET NOT NULL` (PG 12+ skips the scan), then drop the check |
   | `ADD UNIQUE` / `PRIMARY KEY` | `CREATE UNIQUE INDEX CONCURRENTLY`, then `ADD CONSTRAINT … USING INDEX` |
   | `ALTER COLUMN … TYPE` (rewrite) | add a new column, dual-write, backfill in batches, switch reads, drop the old column later |
   | `ADD COLUMN … DEFAULT <volatile>` (e.g. `gen_random_uuid()`) | add the column without a default, backfill in batches, then set the default for new rows |
   | `RENAME COLUMN` / `DROP COLUMN` / `RENAME TABLE` | expand/contract: ship code that stops using it first, drop or rename in a later deploy |
   | Unbatched `UPDATE` / `DELETE` backfill | batches of 1–10k rows by primary key, each in its own transaction, with a pause between batches |

6. **Set a lock timeout** at the top of every migration that takes `ACCESS EXCLUSIVE`:
   `SET lock_timeout = '5s';` — even a brief lock waits behind long transactions and queues all
   traffic behind itself. If it times out, retry at a quieter moment rather than raising the timeout.
7. **Disable the wrapping transaction** for `CONCURRENTLY` steps using the framework setting
   (`atomic = False`, `disable_ddl_transaction!`, `autocommit_block()`), and keep each such step in
   its own migration.

### 4. Order the rollout

8. **Write the deploy order:** which migrations ship before the code change, which ship with it,
   and which ship after it (contract steps only after no running code uses the old shape).
9. **Re-run the linter** on the rewritten SQL and show it is clean, or explain each accepted warning
   (e.g. a `DROP COLUMN` in a contract migration that ships after the code no longer reads it).

## Checklist

```text
- [ ] Got the generated SQL (not just the ORM DSL)
- [ ] Ran scripts/lint_migration.py
- [ ] Checked size and write traffic of each table touched
- [ ] Indexes built CONCURRENTLY, in their own non-transactional migration
- [ ] Constraints added NOT VALID, validated separately
- [ ] No type changes or volatile defaults on large tables; expand/contract instead
- [ ] No renames/drops of columns the running code still uses
- [ ] Backfills batched by primary key
- [ ] SET lock_timeout on migrations taking ACCESS EXCLUSIVE
- [ ] Deploy order written (before / with / after the code)
- [ ] Re-linted the rewritten SQL
```

## Red Flags

- "It ran in two seconds on staging."
- "It's just adding an index."
- "We'll rename the column and update the code in the same deploy."
- "The migration timed out, let's raise lock_timeout."
- "The backfill is one UPDATE, it'll be fine overnight."

## Common Rationalizations

| Excuse | Reality |
|---|---|
| "It's fast on staging." | Staging tables are small and idle; production locks wait behind real transactions and block real traffic. |
| "Deploys are quick, a rename is fine." | During any rolling deploy, old and new code run together. The old code breaks the moment the column is renamed. |
| "We'll run it at night." | Night traffic still includes jobs and long transactions, and the lock still queues everything behind it. Use the safe pattern anyway. |
| "CONCURRENTLY is slower." | It takes longer but doesn't block writes. Slower and online beats fast and down. |

## Anti-Patterns (What NOT to do)

* **Approving a migration because it ran quickly in dev or CI** — those tables are tiny and idle.
* **`CREATE INDEX CONCURRENTLY` inside a transaction block** — Postgres rejects it, and the
  framework may wrap it for you.
* **Renaming or dropping a column in the same deploy as the code change** — old instances break mid-rollout.
* **Backfilling millions of rows in one `UPDATE`** — long locks, replication lag, and table bloat.
* **Raising `lock_timeout` or `statement_timeout` to make a risky migration "work"** — it then blocks traffic for longer.
* **Treating linter silence as proof of safety** — it knows patterns, not your table sizes or traffic.

## Examples

### Example 1: a migration on a 40M-row table

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

### Example 2: an index in Django

**User:** "Add an index on `Order.customer_email` — Django, Postgres, the table is big."

**Expected output:**

```python
# orders/migrations/0057_order_customer_email_idx.py
from django.contrib.postgres.operations import AddIndexConcurrently
from django.db import migrations, models


class Migration(migrations.Migration):
    atomic = False  # CONCURRENTLY can't run inside a transaction

    dependencies = [("orders", "0056_previous")]

    operations = [
        AddIndexConcurrently(
            "order",
            models.Index(fields=["customer_email"], name="order_customer_email_idx"),
        ),
    ]
```

```text
Also add the index to Order.Meta.indexes so Django's model state matches.

$ python manage.py sqlmigrate orders 0057 > /tmp/0057.sql && python3 scripts/lint_migration.py /tmp/0057.sql
No risky patterns found.

If the build fails partway, it leaves an INVALID index: check
SELECT indexrelid::regclass FROM pg_index WHERE NOT indisvalid; and drop it with
DROP INDEX CONCURRENTLY before retrying.
```

## Quick Reference

| Operation | Safe form |
|---|---|
| New index | `CREATE INDEX CONCURRENTLY`, own migration, no transaction |
| New FK / CHECK | `NOT VALID`, then `VALIDATE CONSTRAINT` later |
| NOT NULL on big table | `CHECK … NOT VALID` → validate → `SET NOT NULL` → drop check |
| Unique / PK | Unique index concurrently → `ADD CONSTRAINT … USING INDEX` |
| Type change | New column, dual-write, batched backfill, switch, drop later |
| Rename / drop | Expand/contract across deploys |
| Backfill | Batches by primary key, own transactions |
| Any ACCESS EXCLUSIVE | `SET lock_timeout = '5s'` first |
| Lock details | `references/postgres-locks.md` |
