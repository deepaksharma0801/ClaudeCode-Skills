---
name: iam-policy-review
description: Reviews AWS IAM policies for wildcards, privilege escalation, public principals, and missing conditions, then rewrites them least-privilege. Use for IAM JSON, Terraform, or CDK policies.
compatibility: Bundled script requires Python 3.8+ (standard library only). AWS IAM policy JSON.
---

# Detailed Instructions

Grant what the workload actually calls, on the resources it actually touches. Every wildcard,
every escalation-capable action, and every public principal needs a reason that survives review.

## Overview

IAM policies drift toward `"Action": "s3:*", "Resource": "*"` because it makes errors go away.
The real danger is usually subtler: `iam:PassRole` on any role, permission-attach actions that let
a principal promote itself, `NotAction` allow-lists that silently include new services, and bucket
policies with `"Principal": "*"`. This skill lints the document with `scripts/iam_lint.py`, checks
what the workload really needs, and produces a scoped replacement.

## Workflow Rules

1. **Get the document:** raw JSON, `aws iam get-policy-version … --query PolicyVersion.Document`,
   Terraform (`aws_iam_policy_document` / `jsonencode`), or CDK `PolicyStatement`. Render
   Terraform/CDK to JSON first (`terraform show -json`, `cdk synth`).
2. **Lint:** `python3 scripts/iam_lint.py policy.json` (or pipe on stdin). It flags full admin,
   service wildcards, `NotAction`/`NotResource` allows, write actions on `Resource: "*"`,
   permission-granting actions, credential takeover actions, `iam:PassRole` on `*`, and public
   principals.
3. **Find what is actually used:** IAM Access Analyzer policy generation from CloudTrail, the
   "last accessed" data in the IAM console (`aws iam generate-service-last-accessed-details`), or
   the code's AWS SDK calls. Prefer evidence over guessing.
4. **Rewrite least-privilege:**
   - Replace `service:*` with the specific actions used.
   - Scope `Resource` to ARNs (with prefixes like `arn:aws:s3:::reports-bucket/exports/*`).
   - Constrain `iam:PassRole` to specific role ARNs plus `iam:PassedToService`.
   - Add conditions where they fit: `aws:SourceVpce`, `aws:PrincipalOrgID`, `aws:RequestedRegion`,
     `aws:SecureTransport`, `s3:prefix`, tag-based `aws:ResourceTag/...`.
   - Replace `Allow` + `NotAction` with explicit allows (`Deny` + `NotAction` is a legitimate guardrail pattern).
5. **Resource policies** (S3, KMS, SQS, SNS, Lambda): `"Principal": "*"` must have a condition
   (`aws:SourceArn`, `aws:SourceAccount`, `aws:PrincipalOrgID`) unless public access is intended
   and documented. Check S3 Block Public Access separately.
6. **Re-lint** the rewritten policy and validate it with `aws accessanalyzer validate-policy`
   when available. Note what the script cannot see: SCPs, permission boundaries, session policies.
7. **Report** findings by severity, the rewritten policy, and what must be tested (deploy to staging,
   watch for `AccessDenied` in CloudTrail).

## Anti-Patterns (What NOT to do)

* Do not fix `AccessDenied` errors by widening to `service:*` or `Resource: "*"`.
* Do not leave `iam:PassRole` unscoped; it lets the holder run code as any role, including admin.
* Do not use `Allow` with `NotAction` to mean "everything except IAM"; new services are included automatically.
* Do not treat a scoped resource as safe for permission-attach actions; scoping to your own user still allows self-escalation.
* Do not remove permissions in production without checking last-accessed data or CloudTrail first.

## Examples

**User:** "Review the policy for our deploy bot."

```json
{"Version": "2012-10-17", "Statement": [
  {"Sid": "DeployBot", "Effect": "Allow",
   "Action": ["s3:*", "lambda:UpdateFunctionCode", "lambda:CreateFunction", "iam:PassRole"],
   "Resource": "*"}]}
```

**Expected output:**

```text
$ python3 scripts/iam_lint.py deploy-bot.json
deploy-bot.json  HIGH   DeployBot  service wildcard 's3:*' includes every current and future action in that service
deploy-bot.json  HIGH   DeployBot  iam:PassRole on Resource "*" lets the holder hand any role (including admin) to a service
deploy-bot.json  MEDIUM DeployBot  write actions on Resource "*": iam:PassRole, lambda:CreateFunction, lambda:UpdateFunctionCode
2 high, 1 other

Risk: with lambda:CreateFunction + unscoped iam:PassRole, anyone holding these credentials can create
a function that runs as an admin role — full account takeover. s3:* also allows deleting every bucket.

CloudTrail (last 90 days) shows the bot only calls s3:PutObject on deploy-artifacts and
lambda:UpdateFunctionCode on api-* functions. It never creates functions.

## Least-privilege version
{"Version": "2012-10-17", "Statement": [
  {"Sid": "UploadArtifacts", "Effect": "Allow",
   "Action": ["s3:PutObject"],
   "Resource": "arn:aws:s3:::deploy-artifacts/releases/*"},
  {"Sid": "UpdateApiFunctions", "Effect": "Allow",
   "Action": ["lambda:UpdateFunctionCode", "lambda:GetFunction"],
   "Resource": "arn:aws:lambda:us-east-1:123456789012:function:api-*"}]}

Re-lint: No over-broad statements found.
Test: run one deploy in staging and check CloudTrail for AccessDenied before rolling out.
```
