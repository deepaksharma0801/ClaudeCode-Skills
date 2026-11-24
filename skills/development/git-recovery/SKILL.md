---
name: git-recovery
description: Recovers lost commits, branches, stashes, and work after a bad reset, rebase, merge, or force-push using reflog and safe undo steps. Use when someone says they lost work or broke their git history.
---

# Detailed Instructions

Almost nothing committed in git is truly lost for weeks: the reflog remembers every place `HEAD`
and each branch pointed. Recovery is safe if you **stop, back up the current state, find the
lost commit, and restore it with a non-destructive command first**. Panicked follow-up commands
(another `reset --hard`, `git gc`, re-cloning) are what actually destroy work.

## When to Use

- "I did `git reset --hard` and lost my changes"
- A rebase or merge went wrong; commits disappeared or conflict resolution was botched
- A branch was deleted, or a force-push overwrote a remote branch
- A dropped or cleared stash, or a detached `HEAD` with commits on it
- Committed to the wrong branch, or need to undo a pushed commit

**Don't use when:** the problem is a secret in history (use `leaked-secret-response` — rotate
first), or the changes were never staged or committed (git has no record; look at editor local
history or IDE backups instead).

## Overview

Git recovery fails in two ways: giving up too early ("it's gone, I'll redo it") or making it worse
with more destructive commands. This skill freezes the state, classifies what was lost (committed,
staged, stashed, or never tracked), finds it with the right tool (reflog, `fsck`, the remote), and
restores it onto a new branch so nothing else is overwritten, then shows how to undo safely next
time.

## Workflow Rules

### 1. Freeze

1. **Stop running commands that move refs.** No `reset --hard`, `checkout -f`, `clean -fd`,
   `gc`, or `prune` until the work is found. Never delete and re-clone the repo — the local reflog
   lives only in this `.git` folder.
2. **Back up the repo as it is:** `cp -R .git ../repo-git-backup` (or the whole folder). Cheap
   insurance before any recovery step.
3. **Mark the current position:** `git branch rescue/current-$(date +%s)` so whatever `HEAD` is now
   can't be lost either.

### 2. Classify what was lost

| Lost thing | Where it can be found |
|---|---|
| Commits (after reset, rebase, amend, deleted branch) | `git reflog`, `git reflog show <branch>` |
| A deleted branch | `git reflog` (look for "checkout: moving from <branch>") |
| Staged but never committed changes | Dangling blobs: `git fsck --lost-found` (file contents only, no names) |
| A dropped stash | `git fsck --unreachable \| grep commit`, then inspect stash-like commits |
| A force-pushed remote branch | Anyone's local copy or reflog; GitHub's PR page / events API; CI checkouts |
| Never-staged edits | Not in git. Editor local history (VS Code Timeline, JetBrains Local History) |

### 3. Find it

4. `git reflog --date=iso | head -50` — find the entry just **before** the bad command
   (e.g. `HEAD@{3}: commit: Add billing export`). Inspect with `git show <sha>` and
   `git log --oneline <sha> -10`.
5. For stashes: `git fsck --unreachable | awk '/commit/ {print $3}' | xargs git log --merges
   --no-walk --oneline` (stashes are merge commits named "WIP on …" / "On …").
6. For staged-only files: `git fsck --lost-found`, then `git show <blob-sha>` on each blob in
   `.git/lost-found/other/` and grep for a distinctive line.

### 4. Restore without overwriting

7. **Restore onto a new branch first:** `git branch recovered/<name> <sha>`. Verify with
   `git log` and `git diff main...recovered/<name>`. Only then move the real branch:
   `git switch <branch> && git reset --hard recovered/<name>` (now safe: the old position is
   saved in `rescue/current-*`).
8. Prefer `git cherry-pick` or `git restore --source=<sha> -- <path>` when only part of the lost
   work is wanted.
9. **For a pushed mistake on a shared branch, use `git revert`, not reset + force-push.** If a
   force-push is truly required, use `git push --force-with-lease` and tell collaborators.
10. **For an overwritten remote branch,** push the recovered sha back:
    `git push origin recovered/<name>:<branch> --force-with-lease`, after agreeing with the team.

### 5. Clean up and prevent

11. Delete the `rescue/*` and `recovered/*` branches and the `.git` backup only after the user
    confirms everything is back.
12. Suggest one prevention that matches the accident: `git rebase --abort` / `git merge --abort`
    mid-way, `ORIG_HEAD` (`git reset --hard ORIG_HEAD` right after a bad rebase), branch
    protection against force-pushes, or `git stash` before risky commands.

## Checklist

```text
- [ ] Stopped destructive commands; .git backed up; rescue branch made
- [ ] Classified: committed / staged / stashed / remote / never tracked
- [ ] Lost sha found in reflog or fsck and inspected with git show / git log
- [ ] Restored onto a new branch and verified before touching the real branch
- [ ] Shared branches fixed with revert or --force-with-lease, team told
- [ ] Rescue branches and backup removed only after user confirms
- [ ] One prevention step suggested
```

## Red Flags

- "Let me just re-clone the repo." (Deletes the only reflog.)
- Running `git gc` or `git prune` "to clean up" before recovery is done.
- Another `reset --hard` to "go back" without noting the current sha first.
- `git push --force` to a shared branch without `--force-with-lease` or telling anyone.
- Saying the work is gone before checking reflog **and** fsck.

## Common Rationalizations

| Excuse | Reality |
|---|---|
| "Reset --hard deletes commits." | It moves a pointer. The commits stay reachable from the reflog (90 days by default for reachable entries, 30 for unreachable). |
| "The branch was deleted, it's gone." | Its last sha is in the reflog; `git branch <name> <sha>` brings it back. |
| "Force-push wiped the remote." | Any clone that fetched before, or the pusher's reflog, still has the commits. |
| "Quicker to rewrite the code." | Reflog lookup takes a minute; rewriting takes hours and reintroduces bugs. |

## Anti-Patterns (What NOT to do)

* **Re-cloning or deleting `.git`** — throws away the reflog, the main recovery source.
* **Running `git gc --prune=now`** — permanently deletes unreachable objects you may need.
* **Restoring straight onto the working branch** — a wrong sha then overwrites more work; use a new branch.
* **Rewriting shared history to undo a pushed commit** — `git revert` is safe for everyone else.
* **Promising recovery of never-staged edits** — git never saw them; check editor history instead.

## Examples

### Example 1: lost commits after `reset --hard`

**User:** "I ran `git reset --hard HEAD~3` instead of `HEAD~1`. Two commits I needed are gone."

**Expected output:**

```text
Don't run any more resets. First, save where you are:
  git branch rescue/current-1732460000

Find the commit before the reset:
  $ git reflog --date=iso | head -5
  9f2c1ab HEAD@{0}: reset: moving to HEAD~3
  e41d7c0 HEAD@{1}: commit: Add CSV export for invoices
  b83a9f2 HEAD@{2}: commit: Validate invoice dates
  ...

e41d7c0 is where you were. Check it:
  git log --oneline e41d7c0 -4

Restore on a new branch, verify, then move your branch:
  git branch recovered/invoices e41d7c0
  git diff HEAD recovered/invoices --stat
  git reset --hard recovered/invoices   # safe now — old position saved in rescue/current-*

You wanted HEAD~1, so to drop only the last commit afterwards:
  git reset --hard HEAD~1
Delete rescue/* and recovered/* once you've confirmed everything's there.
```

### Example 2: undoing a commit that's already pushed to main

**User:** "I pushed a broken commit to main. Should I reset and force-push?"

**Expected output:**

```text
No — others may have pulled main already. Revert it instead; this adds a new commit that undoes
it and keeps history intact for everyone:
  git revert <sha>
  git push

If the commit was a merge: git revert -m 1 <merge-sha>.
Force-pushing main would break every teammate's clone and is usually blocked by branch
protection anyway.
```

## Quick Reference

| Situation | Command |
|---|---|
| Find where HEAD was | `git reflog --date=iso` |
| Undo the last rebase/merge/reset | `git reset --hard ORIG_HEAD` (right after it) |
| Recover a deleted branch | `git branch <name> <sha-from-reflog>` |
| Recover a dropped stash | `git fsck --unreachable \| grep commit`, then `git stash apply <sha>` |
| Recover staged-only files | `git fsck --lost-found`, inspect `.git/lost-found/other/` |
| Take one file from an old commit | `git restore --source=<sha> -- path` |
| Undo a pushed commit | `git revert <sha>` |
| Safe force-push | `git push --force-with-lease` |
