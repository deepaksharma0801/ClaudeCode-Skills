---
name: codebase-onboarding
description: Maps an unfamiliar codebase into a short tour of entry points, architecture, key flows, and how to run it. Use when a user opens a new repo and asks how it works or where to start.
---

# Detailed Instructions

Read before you summarize, and cite files for every claim. The output is a map a new engineer can
follow on day one, not a list of every directory.

## Overview

Asked "how does this repo work?", models tend to restate the README or list folders alphabetically.
This skill finds how the code actually starts, how a request or job moves through it, and how to
run and test it locally — and says where it is unsure.

## Workflow Rules

1. **Identify the stack** from manifests and config: `package.json`, `pyproject.toml`, `go.mod`,
   `Cargo.toml`, `Gemfile`, `pom.xml`, `Dockerfile`, `docker-compose.yml`, CI workflows.
2. **Find entry points:** `main` functions, server startup, CLI definitions, route tables, job
   schedulers, `bin/` scripts, and the `scripts` section of the package manifest.
3. **Trace one real flow end to end** (an HTTP request, a CLI command, or a background job): from
   entry point through the layers to storage or output, naming each file and function.
4. **Sketch the architecture** as 4–8 components with one line each and how they talk to each
   other. Use a small Mermaid diagram when it helps.
5. **Run and test:** the exact commands to install, start, and test, taken from the README,
   Makefile, CI config, or manifests. Note required env vars by name (from `.env.example` or code),
   never their values.
6. **Conventions:** where tests live, how config is loaded, error-handling and logging patterns,
   code generation steps, anything that would surprise a newcomer.
7. **Where to start:** 3 good first files to read, and where a typical change (new endpoint, new
   field) would go.
8. **Unknowns:** list anything you could not determine from the code.

## Anti-Patterns (What NOT to do)

* Do not list every directory or file. Group and summarize.
* Do not describe behavior you inferred from names without opening the file.
* Do not copy the README; verify it against the code and note where it is out of date.
* Do not print secrets or values from `.env` files.
* Do not run migrations, seeds, or deploy scripts to "see what happens".

## Examples

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
src/routes/invoices.ts:22 createInvoice → src/services/invoice.ts:40 InvoiceService.create
→ prisma.invoice.create → enqueues "render-pdf" (src/jobs/renderPdf.ts) → uploads to S3

## Architecture
API (Fastify) → Services (business logic) → Prisma → Postgres
API → Redis queue → Worker → S3 / email provider

## Run it
cp .env.example .env    # needs DATABASE_URL, REDIS_URL, S3_BUCKET
docker compose up -d db redis
npm install && npx prisma migrate dev
npm run dev             # API on :3000
npm run worker          # in a second terminal
npm test

## Conventions
- Tests sit next to code as *.test.ts; DB tests use a per-test transaction (test/setup.ts).
- Errors: throw AppError subclasses (src/errors.ts); a Fastify hook maps them to HTTP codes.

## Start here
1. src/services/invoice.ts  2. src/routes/index.ts  3. src/jobs/renderPdf.ts

## Unknowns
- README mentions a `seed` script that no longer exists in package.json.
```
