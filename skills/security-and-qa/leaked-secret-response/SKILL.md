---
name: leaked-secret-response
description: Runs the response when an API key, token, password, or private key is exposed in git, chat, or logs. Rotate first, check for abuse, then clean up. Use the moment a secret leaks.
---

# Detailed Instructions

Rotate first, clean up second. Once a secret has been pushed, shared, or logged, assume it is
compromised — deleting the commit or the message does not take it back, because bots scrape public
repos within minutes and forks, caches, and clones keep copies.
Every minute a leaked credential stays valid is a minute it can be used; cleanup feels productive
but protects nothing until the credential is dead.

## When to Use

- A secret was pushed to git (public or private), pasted in chat, a ticket, or a doc
- A secret appeared in CI logs, error tracking, or application logs
- A provider (GitHub, AWS) emailed about an exposed credential
- A laptop or account with stored credentials was lost or compromised

**Don't use when:** the secret hasn't left the machine yet (use `secrets-precommit-check` to
remove it before committing).

## Overview

The instinct after leaking a key is to rewrite git history and hope. That leaves a working
credential in someone else's hands. This skill runs the response in the right order: contain
(revoke or rotate), assess (was it used?), clean up (history, logs, caches), and prevent (scanning
and push protection), with a short record of what happened.

## Workflow Rules

1. **Identify** the secret: provider (AWS, GitHub, Stripe, OpenAI/Anthropic, database, signing key),
   its permissions, where it was exposed (public or private repo, CI log, chat, ticket), and since when.
2. **Contain — rotate or revoke now**, at the provider:
   - Create a new credential, update every consumer (env vars, secret manager, CI secrets), deploy,
     then revoke the old one. If you can't update consumers quickly and the exposure is public,
     revoke immediately and accept the outage.
   - AWS: deactivate, then delete the access key; check for new IAM users, keys, or roles created
     with it. GitHub: revoke the token in settings. Database passwords: change the password and
     kill existing sessions. Signing keys (JWT, webhooks): rotate and invalidate tokens signed with
     the old key.
3. **Assess abuse** in the provider's logs for the exposure window: AWS CloudTrail (calls by that
   access key ID, unusual regions, new resources), GitHub audit log, Stripe or cloud billing
   anomalies, database connection logs. Record what you find, including "no use found".
4. **Clean up** after rotation, not instead of it:
   - Remove the secret from the code and load it from the environment or a secret manager.
   - Rewrite history only when needed (`git filter-repo --replace-text`), coordinate force-pushes
     with the team, and note that forks and existing clones still contain it.
   - For public GitHub repos, cached views of removed commits may need GitHub Support to purge.
   - Delete it from CI logs, chat messages, and tickets where possible.
5. **Prevent:** enable secret scanning and push protection (GitHub, GitLab), add a pre-commit
   scanner (gitleaks), and move the credential type to short-lived tokens (OIDC for CI) where
   possible.
6. **Record** a short timeline: exposed at, detected at, rotated at, abuse found (yes/no), cleanup
   done, prevention added. Notify security or affected parties per policy.

## Checklist

```text
- [ ] Secret identified: provider, permissions, where exposed, since when
- [ ] Rotated/revoked at the provider (consumers updated, or revoked immediately if public)
- [ ] Related secrets in the same file rotated too
- [ ] Provider logs checked for the exposure window; result recorded
- [ ] Removed from code; loaded from env/secret manager
- [ ] History, logs, chats cleaned where possible (after rotation)
- [ ] Prevention added: push protection, pre-commit scanner, short-lived creds
- [ ] Timeline recorded; security/affected parties notified per policy
```

## Red Flags

- "Let me rewrite history first."
- "It's a private repo / the message is deleted, so it's fine."
- "It only had read access, skip the log check."
- Pasting the secret into a ticket while investigating.

## Common Rationalizations

| Excuse | Reality |
|---|---|
| "Nobody saw it, it was only up for a minute." | Bots scan public pushes within minutes. Assume it was seen. |
| "Rotating will cause an outage." | A brief planned outage beats an attacker with valid credentials. Coordinate fast, but rotate. |
| "We deleted the commit." | Forks, clones, caches, and CI logs keep it. Only rotation helps. |

## Anti-Patterns (What NOT to do)

* Do not rewrite history or delete the message first and rotate later (or never).
* Do not assume a private repo or a deleted chat message means the secret is safe.
* Do not paste the leaked secret into tools, tickets, or searches while investigating; refer to it by its ID or last 4 characters.
* Do not skip checking for abuse because the key "only had read access".
* Do not revoke without a plan for consumers when a coordinated rotation is possible and the exposure is private.

## Examples

### Example 1: AWS keys pushed to a public repo

**User:** "I just pushed our .env with the AWS keys to our public GitHub repo about 20 minutes ago. What do I do?"

**Expected output:**

```text
Treat the key as compromised — public repos are scraped within minutes. Rotate before touching git.

## 1. Contain (now)
- IAM → Users → <deploy user> → Security credentials: create a new access key, then
  deactivate the leaked key (AKIA…7Q2M). If the app can't be updated in the next few minutes,
  deactivate first anyway; a short outage beats a compromised account.
- Update the key in your secret store / hosting env vars and redeploy. Then delete the old key.
- Rotate anything else in that .env (DATABASE_URL password, STRIPE key, JWT secret).

## 2. Check for abuse (window: push time → deactivation)
- CloudTrail → Event history, filter "AWS access key" = AKIA…7Q2M: look for calls you didn't make,
  especially RunInstances, CreateUser, CreateAccessKey, or activity in unusual regions.
- Billing → Cost Explorer: unexpected EC2 or Lambda spend.
- Check for new IAM users, access keys, or roles created in the window.

## 3. Clean up (after rotation)
- git rm --cached .env, add .env to .gitignore, commit .env.example with placeholders.
- Optional history rewrite: git filter-repo --path .env --invert-paths, then force-push and tell
  collaborators to re-clone. Forks and clones still have it — rotation is what actually protects you.

## 4. Prevent
- Enable GitHub secret scanning + push protection on the repo.
- Add gitleaks as a pre-commit hook.
- For CI, switch to GitHub Actions OIDC → AWS role instead of long-lived keys.

## Record
Exposed 14:02 · detected 14:20 · key deactivated 14:24 · CloudTrail: no foreign calls found ·
history cleaned 15:10 · push protection on.
```

### Example 2: a token pasted in a shared chat

**User:** "I accidentally pasted our GitHub personal access token into a Slack channel with 200 people. I deleted the message."

**Expected output:**

```text
Treat it as exposed — 200 people (and any integrations or exports on that channel) could have
copied it before deletion.

1. Now: GitHub → Settings → Developer settings → Personal access tokens → revoke that token.
2. Create a replacement with the minimum scopes and an expiry (fine-grained token, only the repos
   it needs), and update wherever the old one was used.
3. Check: the organization audit log for actions by your account since the paste (repo clones,
   new deploy keys, new tokens, settings changes). Record "no unexpected activity" if clean.
4. Slack: deleting the message was right; ask a workspace admin whether message exports or
   integrations retained it.
5. Prevent: store tokens in a password manager and paste from there; prefer GitHub Apps or
   short-lived tokens over long-lived personal tokens.
```

## Quick Reference

| Order | Action |
|---|---|
| 1 | Rotate or revoke at the provider |
| 2 | Update consumers (secret manager, CI, env vars) |
| 3 | Check provider logs for the exposure window |
| 4 | Remove from code; clean history/logs/chats |
| 5 | Prevent: push protection, scanners, short-lived creds |
| Never | Rewrite history *instead of* rotating; paste the secret while investigating |
