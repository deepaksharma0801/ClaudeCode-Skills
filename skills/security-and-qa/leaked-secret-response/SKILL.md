---
name: leaked-secret-response
description: Runs the response when an API key, token, password, or private key is exposed in git, chat, or logs. Rotate first, check for abuse, then clean up. Use the moment a secret leaks.
---

# Detailed Instructions

Rotate first, clean up second. Once a secret has been pushed, shared, or logged, assume it is
compromised — deleting the commit or the message does not take it back, because bots scrape public
repos within minutes and forks, caches, and clones keep copies.

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

## Anti-Patterns (What NOT to do)

* Do not rewrite history or delete the message first and rotate later (or never).
* Do not assume a private repo or a deleted chat message means the secret is safe.
* Do not paste the leaked secret into tools, tickets, or searches while investigating; refer to it by its ID or last 4 characters.
* Do not skip checking for abuse because the key "only had read access".
* Do not revoke without a plan for consumers when a coordinated rotation is possible and the exposure is private.

## Examples

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
