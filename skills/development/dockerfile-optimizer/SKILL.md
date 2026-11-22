---
name: dockerfile-optimizer
description: Reviews and rewrites a Dockerfile for smaller images, faster cached builds, and safer defaults. Use when a user shares a Dockerfile, or says their image is too big, builds are slow, or runs as root.
---

# Detailed Instructions

Optimize in order: correctness, security, cache efficiency, size. Explain each change with its
effect, and keep the image's runtime behavior identical.

## Overview

Most Dockerfiles copy the whole repo before installing dependencies, ship compilers to production,
and run as root. This skill applies a known set of fixes — layer ordering, multi-stage builds,
slim bases, a non-root user, a `.dockerignore` — and estimates the impact.

## Workflow Rules

1. Read the Dockerfile, `.dockerignore` (or note it is missing), and the manifest/lockfile it uses.
2. **Cache order:** copy only dependency manifests and lockfiles, install dependencies, *then* copy
   the source. Use the lockfile-respecting install (`npm ci`, `pip install --no-cache-dir -r`,
   `go mod download`, `bundle install --deployment`).
3. **Multi-stage:** build or compile in a builder stage; copy only the artifacts into the runtime
   stage. Dev dependencies, compilers, and caches stay behind.
4. **Base image:** pin a specific version tag (`node:20.18-slim`, `python:3.12-slim`), never
   `latest`. Prefer `-slim` or distroless for runtime when compatible; flag `alpine` for musl
   issues with Python wheels or native modules.
5. **Security:** create and switch to a non-root `USER`; no secrets in `ARG`/`ENV`/`COPY` (use
   BuildKit `--mount=type=secret`); add a `HEALTHCHECK` for services if the platform does not
   provide one.
6. **Layer hygiene:** combine `apt-get update && apt-get install --no-install-recommends … && rm -rf
   /var/lib/apt/lists/*` in one `RUN`; use BuildKit cache mounts for package caches.
7. **`.dockerignore`:** at minimum `.git`, `node_modules`, `__pycache__`, `.env*`, test output, local
   build dirs.
8. Use exec-form `CMD ["node", "dist/server.js"]` so signals reach the process.
9. Output the full rewritten Dockerfile, the `.dockerignore`, and a table of changes. Give the
   build command to compare sizes (`docker images`); do not claim a size you did not measure.

## Anti-Patterns (What NOT to do)

* Do not change the app's start command, exposed port, or environment without saying so.
* Do not switch to `alpine` or distroless without checking native dependencies and shell usage.
* Do not bake secrets, `.env` files, or credentials into any layer, even a builder stage.
* Do not use `latest` tags or unpinned `curl | sh` installers.
* Do not state "image is now 80% smaller" without a measured before/after.

## Examples

**User:** "Our Node image is 1.4 GB and rebuilds take forever."

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
COPY --from=build /app/node_modules ./node_modules
COPY --from=build /app/dist ./dist
COPY package.json ./
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
| Copy lockfile before source | Dependency layer is cached; code edits no longer reinstall packages |
| Multi-stage + `npm prune --omit=dev` | Dev dependencies and build tooling stay out of the final image |
| `node:latest` → `node:20.18-slim` | Reproducible builds and a much smaller base |
| `USER node` | Process no longer runs as root |
| Exec-form `CMD` | SIGTERM reaches Node, so shutdowns are graceful |

Measure: `docker build -t app:new . && docker images app` — compare with the old tag.
Check: `npm start` ran `node dist/server.js` (from package.json), so behavior is unchanged.
