# PostgreSQL locks taken by common migration statements

What each statement blocks while it runs, and the framework settings needed for the safe variants.
Source: the PostgreSQL documentation ("Explicit Locking" and the `ALTER TABLE`, `CREATE INDEX`
reference pages).

## Contents

1. [Why even brief locks hurt](#why-even-brief-locks-hurt)
2. [Lock modes by statement](#lock-modes-by-statement)
3. [Framework settings for non-transactional steps](#framework-settings-for-non-transactional-steps)
4. [Finding what is blocked](#finding-what-is-blocked)

## Why even brief locks hurt

An `ACCESS EXCLUSIVE` lock that would take 10 ms still has to **wait** for every transaction
already touching the table — including a long-running report or an idle-in-transaction session.
While it waits, every new query on that table queues **behind it**. A "fast" `ALTER TABLE` can
therefore stall all traffic for as long as the slowest open transaction. That is why every
migration that takes `ACCESS EXCLUSIVE` should start with:

```sql
SET lock_timeout = '5s';   -- fail fast instead of queuing traffic; retry later
```

## Lock modes by statement

| Statement | Lock on the table | Blocks reads? | Blocks writes? | Duration |
|---|---|---|---|---|
| `ALTER TABLE … ADD COLUMN` (no default, or non-volatile default, PG 11+) | ACCESS EXCLUSIVE | yes | yes | brief (catalog only) |
| `ALTER TABLE … ADD COLUMN … DEFAULT <volatile>` | ACCESS EXCLUSIVE | yes | yes | **full table rewrite** |
| `ALTER TABLE … ALTER COLUMN … TYPE` (most changes) | ACCESS EXCLUSIVE | yes | yes | **full rewrite + index rebuild** |
| `ALTER TABLE … ALTER COLUMN … SET NOT NULL` | ACCESS EXCLUSIVE | yes | yes | **full scan** (skipped on PG 12+ if a valid `CHECK (col IS NOT NULL)` exists) |
| `ALTER TABLE … ADD CONSTRAINT … CHECK` | ACCESS EXCLUSIVE | yes | yes | **full scan** (brief with `NOT VALID`) |
| `ALTER TABLE … ADD CONSTRAINT … FOREIGN KEY` | SHARE ROW EXCLUSIVE (both tables) | no | yes | **full scan** (brief with `NOT VALID`) |
| `ALTER TABLE … VALIDATE CONSTRAINT` | SHARE UPDATE EXCLUSIVE | no | no | full scan, but traffic continues |
| `ALTER TABLE … DROP COLUMN` / `RENAME` | ACCESS EXCLUSIVE | yes | yes | brief (catalog only) — but breaks old code |
| `CREATE INDEX` | SHARE | no | yes | **whole build** |
| `CREATE INDEX CONCURRENTLY` | SHARE UPDATE EXCLUSIVE | no | no | slower build; can't run in a transaction |
| `DROP INDEX` | ACCESS EXCLUSIVE | yes | yes | brief |
| `DROP INDEX CONCURRENTLY` | SHARE UPDATE EXCLUSIVE | no | no | can't run in a transaction |
| `REINDEX` (table or index) | blocks writes to the table; reads using that index wait | partly | yes | whole rebuild |
| `REINDEX CONCURRENTLY` (PG 12+) | SHARE UPDATE EXCLUSIVE | no | no | can't run in a transaction |
| `VACUUM FULL`, `CLUSTER` | ACCESS EXCLUSIVE | yes | yes | **full rewrite** |
| `TRUNCATE`, `DROP TABLE` | ACCESS EXCLUSIVE | yes | yes | brief — irreversible |

A failed `CREATE INDEX CONCURRENTLY` leaves an `INVALID` index behind. Find it with
`SELECT indexrelid::regclass FROM pg_index WHERE NOT indisvalid;`, drop it
(`DROP INDEX CONCURRENTLY …`), and retry.

## Framework settings for non-transactional steps

`CONCURRENTLY` statements can't run inside a transaction block, and most migration tools wrap each
migration in one by default.

| Tool | How to run a step outside a transaction |
|---|---|
| Django | `atomic = False` on the migration class; `AddIndexConcurrently` / `RemoveIndexConcurrently` from `django.contrib.postgres.operations` |
| Rails | `disable_ddl_transaction!` in the migration; `add_index … algorithm: :concurrently`. The `strong_migrations` gem flags unsafe operations |
| Alembic | `with op.get_context().autocommit_block():` around `op.create_index(…, postgresql_concurrently=True)` |
| Flyway | Put the statement in its own migration; Flyway detects non-transactional statements on PostgreSQL (check `mixed` / `executeInTransaction` settings for your version) |
| Plain SQL / psql | Don't wrap the statement in `BEGIN … COMMIT` |

Keep each non-transactional step in its **own** migration so a failure doesn't leave half of a
multi-statement migration applied.

## Finding what is blocked

Run during a migration (or an incident) to see who waits on whom:

```sql
SELECT blocked.pid      AS blocked_pid,
       blocked.query    AS blocked_query,
       blocking.pid     AS blocking_pid,
       blocking.query   AS blocking_query,
       now() - blocking.xact_start AS blocking_xact_age
FROM pg_stat_activity blocked
JOIN pg_stat_activity blocking
  ON blocking.pid = ANY (pg_blocking_pids(blocked.pid))
ORDER BY blocking_xact_age DESC;
```

Long-running or `idle in transaction` sessions at the top are what your migration is waiting for.
