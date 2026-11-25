---
name: codebase-onboarding
description: Maps an unfamiliar codebase into a tour of its stack, entry points, one traced flow, architecture, and how to run it. Use when a user opens a new repo or asks how it works or where to start.
---

# Detailed Instructions

Read before you summarize, and cite a file for every claim. The goal is a map a new engineer can
follow on day one — how the code starts, how one real request moves through it, and how to run and
test it — not a tour of every folder. Say plainly where you're unsure; a confident wrong map is
worse than an honest partial one.

## When to Use

- "How does this repo work?" / "Where do I start?" / "Explain this codebase"
- Joining a project, reviewing an unfamiliar service, or picking up someone else's code
- Before making a change in code you haven't read

**Don't use when:** the user asks about one specific function or bug (answer that directly), or
the repo is tiny enough that reading the two main files answers the question.

## Overview

Asked to explain a repo, models tend to restate the README or list directories alphabetically.
Both miss what a newcomer needs: where execution starts, how data flows, and what will surprise
them. This skill identifies the stack from manifests, finds the real entry points, traces one
representative flow end to end with file and function names, sketches the components, extracts
the exact commands to run and test, and lists conventions and unknowns. The output follows a fixed
shape so it's easy to scan.

## Workflow Rules

### 1. Survey (minutes, not hours)

1. **List the top level and the manifests:** `ls`, then read `package.json`, `pyproject.toml` /
   `requirements*.txt`, `go.mod`, `Cargo.toml`, `Gemfile`, `pom.xml` / `build.gradle`,
   `Dockerfile`, `docker-compose.yml`, `Makefile`, and CI workflows (`.github/workflows/*.yml`).
   These tell you the language, framework, services, and the commands that actually run.
2. **Measure before reading:** count files by type (`git ls-files | sed 's/.*\.//' | sort | uniq -c | sort -rn | head`)
   and find the biggest directories. This tells you where the code mass is.
3. **Skim the README and docs**, but treat them as claims to verify — they drift.

### 2. Find how it starts

4. **Locate entry points:** server startup (`main`, `app.listen`, `uvicorn`, `manage.py`), CLI
   definitions, route tables, job schedulers and queue consumers, `bin/` scripts, serverless
   handlers, and the `scripts` section of the manifest.
5. **Find configuration loading:** where env vars are read and which are required (`.env.example`,
   settings modules, `process.env` / `os.environ` usage). Record names, never values.

### 3. Trace one real flow

6. **Pick a representative flow** — the main user action (create an order, run the CLI's primary
   command, process a queue message) — and follow it from entry point through each layer to
   storage or output, naming each file and function. Open every file you name.
7. **Note the layers it crosses:** routing, validation, business logic, data access, external
   calls, background work. This reveals the architecture better than the folder structure does.

### 4. Map and verify

8. **Sketch 4–8 components** with one line each and how they communicate; add a small Mermaid
   diagram when there are more than three moving parts.
9. **Extract run and test commands** from the README, Makefile, manifest scripts, and CI config.
   Prefer what CI runs — it's the version that's known to work. If you can, run the tests to
   confirm.
10. **Collect conventions and surprises:** where tests live, error-handling and logging patterns,
    code generation steps, feature flags, monorepo tooling, anything that would trip a newcomer.
11. **List unknowns** you couldn't determine, and README claims that don't match the code.

### 5. Write it up in this shape

```text
## Stack            one line
## Entry points     file — what starts there
## One flow         entry → layer → layer → storage, with file:line and function names
## Architecture     4–8 components, how they talk (diagram if > 3)
## Run it           exact commands; required env var names
## Conventions      tests, errors, config, codegen, surprises
## Start here       3 files to read first + where a typical change would go
## Unknowns         what couldn't be determined; README drift
```

## Checklist

```text
- [ ] Manifests, Dockerfile, Makefile, and CI config read
- [ ] File counts by type checked
- [ ] Entry points found and opened
- [ ] Config loading and required env var names found
- [ ] One flow traced end to end with file and function names
- [ ] Components sketched (diagram if more than three)
- [ ] Run/test commands taken from CI or scripts (and tried if possible)
- [ ] Conventions and surprises listed
- [ ] Unknowns and README drift listed
```

## Red Flags

- Describing a folder's purpose from its name without opening a file in it.
- A summary with no file paths.
- Skipping the run instructions because the build "probably works".
- Listing every directory instead of tracing one real request.
- Presenting a guess about architecture as fact.

## Common Rationalizations

| Excuse | Reality |
|---|---|
| "The README explains it." | READMEs drift. Check them against the code and CI. |
| "The folder names are self-explanatory." | `utils/` and `core/` hide most of the surprises. |
| "Tracing one flow is slow." | It's the fastest way to learn how the layers really connect. |
| "I'll skip running it." | Then the run instructions are unverified; say so. |

## Anti-Patterns (What NOT to do)

* **Listing every directory or file** — the reader needs the shape, not an index.
* **Describing behavior inferred from names without opening the file** — names lie; cite what you read.
* **Copying the README** — verify it against the code and call out drift.
* **Printing secrets or values from `.env` files** — record variable names only.
* **Running migrations, seeds, or deploy scripts to "see what happens"** — they change shared state.
* **Covering five flows shallowly instead of one deeply** — one complete trace teaches the architecture.

## Examples

### Example 1: a web service

**User:** "I just cloned this, how does it work?"

**Expected output:**

```text
## Stack
TypeScript · Node 20 · Fastify · Postgres via Prisma · BullMQ on Redis · Vitest

## Entry points
- src/server.ts — starts Fastify, registers routes from src/routes/
- src/worker.ts — starts BullMQ workers from src/jobs/
- prisma/schema.prisma — data model (12 tables)

## One flow: POST /invoices
src/routes/invoices.ts:22 createInvoice (zod validation)
→ src/services/invoice.ts:40 InvoiceService.create
→ prisma.invoice.create (src/db.ts client)
→ enqueue "render-pdf" → src/jobs/renderPdf.ts:15 → uploads to S3 → emails customer

## Architecture
API (Fastify) → Services (business logic) → Prisma → Postgres
API → Redis queue → Worker → S3, email provider

## Run it
cp .env.example .env    # needs DATABASE_URL, REDIS_URL, S3_BUCKET, EMAIL_API_KEY
docker compose up -d db redis
npm ci && npx prisma migrate dev
npm run dev             # API on :3000
npm run worker          # second terminal
npm test                # same as CI (.github/workflows/test.yml)

## Conventions
- Tests sit next to code as *.test.ts; DB tests run in a per-test transaction (test/setup.ts).
- Errors: throw AppError subclasses (src/errors.ts); a Fastify hook maps them to status codes.
- Prisma client is generated: run `npx prisma generate` after editing schema.prisma.

## Start here
1. src/services/invoice.ts  2. src/routes/index.ts  3. src/jobs/renderPdf.ts
A new endpoint goes in src/routes/ + a service in src/services/ + a test next to each.

## Unknowns
- README mentions `npm run seed`, which no longer exists in package.json.
- How production runs migrations isn't in this repo (likely the deploy pipeline).
```

### Example 2: a monorepo

**User:** "This monorepo is huge. Where's the actual app?"

**Expected output:**

```text
## Stack
pnpm workspaces + Turborepo; 3 apps, 9 packages (pnpm-workspace.yaml, turbo.json)

## Where the code is (git ls-files, by directory)
apps/web        1,840 files   Next.js 14 customer app        ← the main product
apps/admin        410 files   internal admin (Next.js)
apps/api          960 files   NestJS backend
packages/ui       330 files   shared React components
packages/db        90 files   Drizzle schema + migrations
(7 smaller packages: config, eslint, tsconfig, utils, ...)

## Entry points
apps/web/app/layout.tsx · apps/api/src/main.ts · packages/db/src/schema.ts

## Run one app
pnpm install
pnpm --filter api dev & pnpm --filter web dev
Tests: pnpm turbo test --filter=web...   (the "..." includes its dependencies)

## Start here
apps/web/app/(shop)/checkout/page.tsx → calls apps/api via packages/api-client.
```

## Quick Reference

| Question | Where to look |
|---|---|
| Language, framework, services | Manifests, Dockerfile, docker-compose |
| Commands that really work | CI workflow files, Makefile, manifest scripts |
| Where execution starts | main/server files, route tables, job consumers |
| Required configuration | `.env.example`, settings modules, env var reads |
| Architecture | One traced flow, not the folder tree |
| Where the code mass is | File counts by type and directory |
