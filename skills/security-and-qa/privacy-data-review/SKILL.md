---
name: privacy-data-review
description: Reviews code or a design for how personal data is collected, logged, stored, shared, and deleted. Use when a change touches user data, analytics, logging, third-party SDKs, or data exports.
---

# Detailed Instructions

Follow each piece of personal data from where it enters to everywhere it ends up. Collect less,
keep it for less time, and never let it leak into logs, URLs, or third parties by accident.

## Overview

Privacy problems usually come from ordinary engineering choices: logging a full request body,
putting an email in a URL, sending user IDs to an analytics SDK, keeping data forever because no
one wrote a deletion job. This skill inventories personal data in a change, maps its flows, and
flags concrete issues against common principles (data minimization, purpose limitation, retention,
user rights, security).

## Workflow Rules

1. **Inventory** the personal data the change touches: identifiers (name, email, phone, IP, device
   IDs), sensitive categories (health, financial, precise location, government IDs, children's
   data), and free-text fields that may contain anything.
2. **Map flows** for each item: collected where → stored where (tables, caches, object storage,
   backups) → sent where (logs, analytics, error tracking, third-party APIs, exports, emails).
3. **Check each flow:**
   - **Minimization:** is every field needed for the stated purpose? Could it be aggregated,
     truncated (IP to /24), or hashed?
   - **Leaks:** personal data in logs, error reports, URLs or query strings, analytics events,
     client-side storage, or cache keys.
   - **Third parties:** what is shared, with which vendor, and is it covered by an agreement and
     the privacy notice?
   - **Retention and deletion:** is there a retention period, and does account deletion remove the
     data everywhere, including derived tables and backups on their normal cycle?
   - **Access and export:** can the data be included in a user's access/export request?
   - **Security:** encryption at rest for sensitive fields, least-privilege access, no personal data
     in non-production environments without masking.
4. **Report** each issue: severity, `file:line` or component, the data involved, the risk, and a
   specific fix.
5. Note where legal or policy input is needed (lawful basis, consent, cross-border transfer)
   rather than deciding it.

## Anti-Patterns (What NOT to do)

* Do not give legal conclusions ("this is GDPR-compliant"); identify issues and flag questions for legal review.
* Do not treat hashing an email as anonymization; it is still personal data.
* Do not recommend collecting more data "for future analytics".
* Do not ignore free-text fields; they routinely contain personal and sensitive data.
* Do not copy real personal data from the code, logs, or fixtures into your output.

## Examples

**User:** "We're adding a 'contact support' form that creates a ticket in our helpdesk and logs the request. Anything to worry about?"

**Expected output:**

```text
## Personal data in this change
name, email, account_id, message (free text — may contain anything, including payment or health
details), IP address, user agent, optional attachment.

## Flows
form → POST /support → (1) app logs  (2) support_requests table  (3) Helpdesk API (vendor)
                                      (4) Sentry on errors        (5) analytics event "support_submitted"

## Issues
1. HIGH — support/routes.py:31 logs the full request body (name, email, message) at INFO.
   Fix: log request ID, account_id, and message length only.
2. HIGH — analytics.track("support_submitted", {email, message[:100]}) sends personal data to the
   analytics vendor. Fix: send { account_id_hash, category } or nothing.
3. MEDIUM — Sentry captures request bodies by default. Set send_default_pii=False and scrub
   "email" and "message" in before_send.
4. MEDIUM — support_requests has no retention. Proposed: delete 2 years after ticket closure, and
   include it in the account-deletion job (jobs/delete_account.py does not reference it).
5. LOW — attachments stored in a public-read bucket path. Use a private bucket and signed URLs.

## Needs legal / policy input
- Is the helpdesk vendor listed in the privacy notice, with a data processing agreement in place?
```
