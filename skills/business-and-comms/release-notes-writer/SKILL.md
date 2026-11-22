---
name: release-notes-writer
description: Turns commits, merged PRs, or a changelog into user-facing release notes grouped by what changed for users. Use when preparing a release, changelog entry, version announcement, or "what's new" post.
---

# Detailed Instructions

Write for the people using the product, not the people who built it. Each line says what a user
can now do, or what stopped being broken, in their words.

## Overview

Raw commit logs make poor release notes: internal names, refactors, and "fix typo" drown out the
three changes users care about. This skill collects changes between two versions, filters out the
internal ones, rewrites the rest as user benefits, and puts breaking changes and upgrade steps
where nobody can miss them.

## Workflow Rules

1. Find the range: `git log <previous-tag>..<new-tag or HEAD> --no-merges`, plus merged PR titles
   and bodies if `gh` is available. Note the version number and date.
2. **Classify** each change: New, Improved, Fixed, Breaking, Deprecated, Security, or Internal.
3. **Drop Internal** changes (refactors, CI, test-only, dependency bumps with no user effect) from
   the user-facing notes. Keep a count so nothing looks hidden.
4. **Rewrite** each remaining item as one line in user terms: what changed and why it matters.
   Link the PR or issue.
5. **Breaking changes first**, each with a migration step (old → new, code snippet if needed).
6. Order sections: Breaking, Security, New, Improved, Fixed, Deprecated. Omit empty sections.
7. Match the audience the user names: developers (API names, code) or end users (UI wording,
   no internals).
8. Offer a 1–2 sentence highlight summary for announcements.

## Anti-Patterns (What NOT to do)

* Do not paste commit messages or internal ticket codes as release notes.
* Do not list refactors, test changes, or CI tweaks as features.
* Do not hide breaking changes inside "Improved".
* Do not promise behavior the diff does not implement, or mention unreleased work.
* Do not credit or name contributors unless the project's existing notes do so.

## Examples

**User:** "Write release notes for v2.4.0 from the commits since v2.3.0. Audience: developers using our SDK."

**Expected output:**

````markdown
## v2.4.0 — 2026-11-21

Retries are now built in, and uploads can resume after a dropped connection.

### Breaking
- `client.upload()` now returns an `Upload` object instead of a URL string. Use `upload.url`.
  ```ts
  // before
  const url = await client.upload(file);
  // after
  const { url } = await client.upload(file);
  ```

### New
- Automatic retries with exponential backoff for 5xx and network errors. Configure with
  `new Client({ retries: 3 })` (#212)
- Resumable uploads for files over 50 MB; call `upload.resume()` after a dropped connection (#219)

### Fixed
- `listFiles()` no longer skips the last page when the total is an exact multiple of the page size (#224)
- Timeouts now raise `TimeoutError` instead of a generic `Error` (#226)

### Deprecated
- `client.getUrl()` — use `client.files.get(id).url`. It will be removed in v3.0.

_Also in this release: 14 internal changes (tests, CI, dependency updates)._
````
