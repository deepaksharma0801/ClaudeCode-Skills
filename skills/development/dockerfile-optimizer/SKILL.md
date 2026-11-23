---
name: dockerfile-optimizer
description: Reviews and rewrites a Dockerfile for smaller images, faster cached builds, and safer defaults. Use when sharing a Dockerfile, or when an image is too big, builds are slow, or it runs as root.
---

# Detailed Instructions

Optimize in this order: correctness, security, cache efficiency, size — and keep the container's
runtime behavior identical. Every change is explained by its effect, and size or speed claims come
from a measured before/after, never from expectation. Changing the base image or the start command
is a behavior change; say so explicitly.

## When to Use

- A Dockerfile shared for review, or a new service needing one
- "The image is 1.5 GB", "builds take 10 minutes", "every code change reinstalls dependencies"
- Security review findings: runs as root, secrets in layers, `latest` tags
- CI build-time or registry-storage costs

**Don't use when:** the problem is the app's runtime performance inside the container (use
`performance-investigation`), or orchestration config (Kubernetes manifests, Compose networking)
rather than the image.

## Overview

Most Dockerfiles copy the whole repo before installing dependencies (so every code edit busts the
cache), ship compilers and dev dependencies to production, run as root, and use floating tags.
This skill reviews the file against a fixed list of known fixes — layer ordering, multi-stage
builds, pinned slim bases, a non-root user, BuildKit cache and secret mounts, a `.dockerignore`,
exec-form commands — rewrites it, and measures the result.

## Workflow Rules

### 1. Understand the current build

1. **Read** the Dockerfile, `.dockerignore` (or note it's missing), the dependency manifest and
   lockfile it uses, and how the image is started (CMD/ENTRYPOINT, compose, Kubernetes).
2. **Measure the baseline:** `docker build -t app:before .` (time it), `docker images app:before`
   for size, and `docker history app:before` to see which layers are big.
3. **Note what the runtime needs:** native libraries (libpq, ImageMagick), a shell for entrypoint
   scripts, CA certificates, time zone data, writable directories. These constrain the base image.

### 2. Fix in priority order

4. **Correctness:** use the lockfile-respecting install (`npm ci`, `pip install --no-cache-dir -r
   requirements.txt` with pinned versions, `poetry install --no-root`, `go mod download`,
   `bundle install` with `BUNDLE_DEPLOYMENT=1`). Set `WORKDIR` explicitly.
5. **Security:**
   - Run as a non-root `USER` (the `node` user in official Node images; otherwise create one with
     a fixed UID, e.g. 10001, so Kubernetes `runAsNonRoot` can verify it).
   - No secrets in `ARG`, `ENV`, or copied files — they persist in image layers and history. Use
     BuildKit secret mounts: `RUN --mount=type=secret,id=npmrc,target=/root/.npmrc npm ci`.
   - Pin base images to a specific version tag (`node:20.18-slim`), and for strict
     reproducibility, a digest (`@sha256:…`). Never `latest`.
6. **Cache efficiency:** copy only the manifest and lockfile, install dependencies, *then* copy the
   source. Put rarely changing steps first. Use BuildKit cache mounts for package-manager caches
   (`RUN --mount=type=cache,target=/root/.npm npm ci`). Add a `# syntax=docker/dockerfile:1`
   line so BuildKit features are available.
7. **Size:** multi-stage builds — compile in a builder stage, copy only artifacts and production
   dependencies to the runtime stage. Prefer `-slim` bases; consider distroless for runtime only
   when the app needs no shell and you've checked native dependencies. Flag Alpine for musl issues
   with Python wheels and some native Node modules.
8. **Layer hygiene:** combine `apt-get update && apt-get install -y --no-install-recommends … &&
   rm -rf /var/lib/apt/lists/*` in one `RUN` so the package index doesn't persist.
9. **`.dockerignore`:** at minimum `.git`, `node_modules`, `__pycache__`, `.venv`, `.env*`,
   `coverage`, local build output, and test fixtures not needed at runtime. It shrinks the build
   context and prevents secrets being copied in.
10. **Process handling:** exec-form `CMD ["node", "dist/server.js"]` so the app is PID 1 and
    receives SIGTERM; add `--init` (or `tini`) if the app spawns children. Add a `HEALTHCHECK`
    only if the platform doesn't already probe health.

### 3. Verify

11. **Rebuild and measure:** `docker build -t app:after .`, compare size and build time, and time
    a rebuild after a one-line code change to prove the dependency layer is cached.
12. **Run it:** start the container, hit a health endpoint or run the CLI, and confirm it runs as
    non-root (`docker run --rm app:after id`).
13. **Report** the rewritten Dockerfile, the `.dockerignore`, a change table (change → effect),
    measured before/after numbers, and any behavior change (base OS, user, start command).

## Checklist

```text
- [ ] Baseline size, build time, and layer sizes measured
- [ ] Runtime needs noted (native libs, shell, certs, tzdata)
- [ ] Lockfile-respecting install
- [ ] Non-root USER with fixed UID
- [ ] No secrets in ARG/ENV/COPY; BuildKit secret mounts if needed
- [ ] Base image pinned (tag, digest if strict)
- [ ] Manifest/lockfile copied before source
- [ ] Multi-stage; dev deps and toolchains left behind
- [ ] .dockerignore covers .git, deps, env files, build output
- [ ] Exec-form CMD
- [ ] Rebuilt, measured, run, and non-root confirmed
```

## Anti-Patterns (What NOT to do)

* **Changing the start command, port, or environment silently** — that's a behavior change; call it out.
* **Switching to Alpine or distroless without checking native dependencies and shell usage** — builds pass, runtime crashes.
* **Baking secrets into any layer, even a builder stage** — `docker history` and layer extraction reveal them.
* **`latest` tags or unpinned `curl | sh` installers** — builds stop being reproducible and can change under you.
* **Claiming "80% smaller" without measuring** — report the actual `docker images` numbers.
* **`RUN apt-get update` in its own layer** — the stale index gets cached and later installs fail or install old versions.

## Examples

### Example 1: a typical Node service

**User:** "Our Node image is 1.4 GB and every rebuild reinstalls everything."

```dockerfile
FROM node:latest
COPY . /app
WORKDIR /app
RUN npm install
RUN npm run build
CMD npm start
```

**Expected output:**

```dockerfile
# syntax=docker/dockerfile:1
FROM node:20.18-slim AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN --mount=type=cache,target=/root/.npm npm ci
COPY . .
RUN npm run build && npm prune --omit=dev

FROM node:20.18-slim
WORKDIR /app
ENV NODE_ENV=production
COPY --from=build --chown=node:node /app/node_modules ./node_modules
COPY --from=build --chown=node:node /app/dist ./dist
COPY --chown=node:node package.json ./
USER node
EXPOSE 3000
CMD ["node", "dist/server.js"]
```

```text
.dockerignore
.git
node_modules
dist
.env*
coverage
```

| Change | Effect |
|---|---|
| Lockfile copied before source | Dependency layer cached; code edits no longer reinstall packages |
| Multi-stage + `npm prune --omit=dev` | Dev dependencies and build tooling stay out of the final image |
| `node:latest` → `node:20.18-slim` | Reproducible builds; much smaller base (Debian slim) |
| `USER node` | Process no longer runs as root |
| Exec-form `CMD` | SIGTERM reaches Node, so shutdowns are graceful |
| `.dockerignore` | Build context drops `.git`, local `node_modules`, and `.env` files |

Measured (same machine): 1.41 GB → 212 MB. Rebuild after a one-line code change: 2m 40s → 9s.
Behavior check: `npm start` ran `node dist/server.js` (package.json), so the start command is
unchanged. `docker run --rm app:after id` → uid=1000(node).

### Example 2: a Python app with a native dependency

**User:** "Can we switch our Django image to Alpine to make it smaller?"

**Expected output:**

```text
Not recommended here. requirements.txt includes psycopg2 (not -binary), Pillow, and lxml. On
Alpine (musl) pip often can't use prebuilt manylinux wheels, so these compile from source:
build time grows, you need gcc and -dev packages in the build stage, and runtime libraries
(libpq, libjpeg, libxml2) still have to be installed.

Better: python:3.12-slim with a multi-stage build that compiles wheels in the builder and copies
only the installed packages:

FROM python:3.12-slim AS build
RUN apt-get update && apt-get install -y --no-install-recommends build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt

FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends libpq5 \
    && rm -rf /var/lib/apt/lists/* && useradd --uid 10001 --create-home app
COPY --from=build /wheels /wheels
RUN pip install --no-cache-dir /wheels/* && rm -rf /wheels
WORKDIR /app
COPY --chown=app:app . .
USER app
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000"]

Measure both before deciding; keep Alpine only if it's meaningfully smaller and every native
package works in a smoke test.
```

## Quick Reference

| Problem | Fix |
|---|---|
| Every code change reinstalls deps | Copy manifest + lockfile, install, then copy source |
| Image too big | Multi-stage; slim base; prune dev deps; `.dockerignore` |
| Runs as root | `USER` with fixed UID |
| Secret needed at build time | `RUN --mount=type=secret,...` |
| Slow package installs | `RUN --mount=type=cache,target=...` |
| Container ignores SIGTERM | Exec-form `CMD`; `--init` if it spawns children |
| Floating versions | Pin tag; digest for strict reproducibility |
