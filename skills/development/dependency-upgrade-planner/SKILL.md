---
name: dependency-upgrade-planner
description: Plans and executes major-version upgrades of a framework or library using changelogs, codemods, and small verified steps. Use for requests like upgrading to React 19 or Django 5.
---

# Detailed Instructions

Upgrade one major version at a time, with the test suite green between steps. Read the official
migration guide before changing anything — most breakage is documented, and most upgrades have a
codemod for the mechanical part.

## Overview

Big-bang upgrades ("bump everything and fix what breaks") produce huge diffs, mixed failures, and
rollbacks. This skill inventories what is installed, reads the release notes for every major
version being crossed, fixes deprecation warnings on the current version first, applies official
codemods, and upgrades in steps that can each be tested and reverted.

## Workflow Rules

1. **Inventory:** current and target versions (from the lockfile, not the manifest range), the
   runtime version, and the packages that depend on the one being upgraded (peer dependencies,
   plugins, type packages). Check that each has a compatible release.
2. **Read the sources** for every major version crossed: official upgrade/migration guide,
   CHANGELOG or release notes (breaking changes section), and deprecation lists. Summarize the
   breaking changes that touch this codebase (search the code for each removed API).
3. **Prepare on the current version:** turn on deprecation warnings
   (`python -W error::DeprecationWarning`, `node --throw-deprecation`, framework-specific flags),
   fix them, and make sure the suite is green. This step often removes most of the upgrade work.
4. **Use official codemods** where they exist (e.g. `npx @next/codemod`, `npx codemod react/19/...`,
   `django-upgrade --target-version`, `pyupgrade`, `rector` for PHP, `ng update` for Angular).
   Review their diff like any other change.
5. **Upgrade in steps:** one major version per commit or PR (e.g. 3 → 4, test, then 4 → 5) — or LTS to
   LTS where the project documents that path (Django 3.2 → 4.2) — updating
   companion packages together. Regenerate the lockfile with the package manager, never by hand.
6. **Verify each step:** full test suite, type check, build, and a smoke test of key flows. Watch
   for runtime-only breakage the tests miss (config keys renamed, default behavior changes).
7. **Plan the rollout:** staging first, monitor errors, and keep the previous version deployable.
8. **Report** the plan or result: versions crossed, breaking changes that applied and how they were
   handled, codemods run, test results per step, and anything left as follow-up.

## Anti-Patterns (What NOT to do)

* Do not jump several major versions in one step without reading each version's guide.
* Do not upgrade every dependency at once alongside the target upgrade.
* Do not silence deprecation warnings instead of fixing them.
* Do not hand-edit lockfiles.
* Do not rely on memory for what changed in a version; cite the changelog or migration guide.
* Do not declare done when tests pass but the app was never started or smoke-tested.

## Examples

**User:** "Upgrade our Django 3.2 app to Django 5.1."

**Expected output:**

```text
## Inventory
Django 3.2.25 (lockfile), Python 3.9. Django 5.1 requires Python 3.10+, so Python goes first.
Companion packages: djangorestframework 3.12 → 3.15, django-filter 2.4 → 24.x, celery unaffected.

## Path (one PR each, suite green between)
0. Python 3.9 → 3.12 (separate PR; CI image + Dockerfile).
1. Django 3.2 → 4.2 LTS
2. Django 4.2 → 5.0
3. Django 5.0 → 5.1

## Breaking changes that touch this codebase (from the 4.0–5.1 release notes)
- 4.0: `django.utils.translation.ugettext` and friends removed → 14 uses (django-upgrade rewrites them)
- 4.0: `USE_L10N` deprecated; `CSRF_TRUSTED_ORIGINS` now requires the scheme → settings/prod.py
- 4.2: `index_together` deprecated → 3 models; replace with Meta.indexes (removed in 5.1)
- 4.2: `DEFAULT_FILE_STORAGE` / `STATICFILES_STORAGE` deprecated in favor of STORAGES (removed in 5.1)
- 5.0: form fields render with `aria-describedby` and new template defaults → snapshot tests

## Step 1 (3.2 → 4.2), done
- python -W error::DeprecationWarning manage.py test on 3.2 → fixed 22 warnings first
- django-upgrade --target-version 4.2 $(git ls-files '*.py') → 31 files changed
- Updated CSRF_TRUSTED_ORIGINS to include https://
- Tests: 1,284 passed. Type check clean. Staging smoke test: login, checkout, admin OK.

## Next
Step 2 (4.2 → 5.0): STORAGES setting, Meta.indexes, form snapshot updates. Estimated half a day.
```
