#!/usr/bin/env python3
"""Flag over-broad and escalation-prone statements in AWS IAM policy JSON. Stdlib only (Python 3.8+).

Usage:
    python3 iam_lint.py policy.json [more.json ...]
    aws iam get-policy-version --policy-arn ARN --version-id v3 --query PolicyVersion.Document | python3 iam_lint.py -

Accepts a policy document ({"Version", "Statement"}), a list of statements, or Terraform-style
JSON with a "policy" string. Exit code: 1 if any HIGH finding.
This is a static check of the document only; it does not know about SCPs, permission boundaries,
or resource policies elsewhere in the account. Use IAM Access Analyzer for account-wide analysis.
"""
import fnmatch
import json
import sys

# Privilege-escalation actions (iam:PassRole is checked separately).
# Granting permissions: dangerous even on a scoped resource, since the holder can attach admin
# rights to that principal (often itself), unless a Condition limits which policies.
GRANT_ESCALATION = [
    "iam:CreatePolicyVersion", "iam:SetDefaultPolicyVersion",
    "iam:AttachUserPolicy", "iam:AttachGroupPolicy", "iam:AttachRolePolicy",
    "iam:PutUserPolicy", "iam:PutGroupPolicy", "iam:PutRolePolicy",
    "iam:UpdateAssumeRolePolicy",
]
# Credential and membership actions: normal for self-service on your own user ARN, escalation
# when they apply to other users or groups.
CREDENTIAL_ESCALATION = [
    "iam:CreateAccessKey", "iam:CreateLoginProfile", "iam:UpdateLoginProfile", "iam:AddUserToGroup",
]
# Write-like verbs: a wildcard resource with these is a much bigger blast radius than with reads.
WRITE_PREFIXES = ("Put", "Create", "Delete", "Update", "Attach", "Detach", "Modify", "Set",
                  "Add", "Remove", "Terminate", "Run", "Start", "Stop", "Pass", "Invoke", "Write")


def as_list(v):
    return v if isinstance(v, list) else ([] if v is None else [v])


def matches(pattern, action):
    return fnmatch.fnmatchcase(action.lower(), pattern.lower())


def load(text, name):
    try:
        doc = json.loads(text)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"error: {name} is not valid JSON: {exc}")
    if isinstance(doc, dict) and isinstance(doc.get("policy"), str):
        doc = json.loads(doc["policy"])
    if isinstance(doc, dict) and "Statement" in doc:
        return as_list(doc["Statement"])
    if isinstance(doc, list):
        return doc
    raise SystemExit(f"error: {name}: no 'Statement' found")


def lint_statement(i, st):
    out = []
    add = lambda sev, msg: out.append((sev, st.get("Sid") or f"#{i}", msg))
    if st.get("Effect") != "Allow":
        return out
    actions = as_list(st.get("Action"))
    resources = as_list(st.get("Resource"))
    has_condition = bool(st.get("Condition"))

    if "NotAction" in st:
        add("HIGH", "Allow with NotAction grants every action except the listed ones, including future services")
    if "NotResource" in st:
        add("MEDIUM", "Allow with NotResource applies to every resource except the listed ones")

    if any(a == "*" for a in actions):
        add("HIGH", "Action \"*\" grants full administrator access" + ("" if "*" in resources else " on these resources"))
    for a in actions:
        if a != "*" and a.endswith(":*"):
            add("MEDIUM" if "*" not in resources else "HIGH",
                f"service wildcard {a!r} includes every current and future action in that service")

    wildcard_res = "*" in resources
    write_actions = [a for a in actions if a != "*" and not a.endswith(":*")
                     and a.split(":", 1)[-1].startswith(WRITE_PREFIXES)]
    if wildcard_res and write_actions and not has_condition:
        add("MEDIUM", f"write actions on Resource \"*\": {', '.join(sorted(set(write_actions))[:5])}"
                      + (" ..." if len(set(write_actions)) > 5 else ""))

    grant = sorted({e for e in GRANT_ESCALATION for a in actions if matches(a, e)})
    if grant:
        add("HIGH" if not has_condition else "MEDIUM",
            "can grant permissions (privilege escalation): " + ", ".join(grant)
            + ("" if not has_condition else "; Condition present, confirm it limits which policies"))
    creds = sorted({e for e in CREDENTIAL_ESCALATION for a in actions if matches(a, e)})
    if creds:
        own_user = all("${aws:username}" in r for r in resources) and resources
        if wildcard_res:
            add("HIGH", "credential/group actions on Resource \"*\" let the holder take over other users: "
                + ", ".join(creds))
        elif not own_user:
            add("MEDIUM", "credential/group actions on other principals: " + ", ".join(creds)
                + "; confirm the targets are not more privileged")

    if any(matches(a, "iam:PassRole") for a in actions) and wildcard_res:
        add("HIGH", "iam:PassRole on Resource \"*\" lets the holder hand any role (including admin) to a service")

    principals = st.get("Principal")
    if principals == "*" or (isinstance(principals, dict) and "*" in as_list(principals.get("AWS"))):
        if not has_condition:
            add("HIGH", "Principal \"*\" without a Condition makes this resource public")
        else:
            add("LOW", "Principal \"*\" restricted only by Condition; confirm the condition keys")
    return out


def main(argv):
    paths = argv[1:] or ["-"]
    findings = []
    for path in paths:
        text = sys.stdin.read() if path == "-" else open(path, encoding="utf-8").read()
        for i, st in enumerate(load(text, path)):
            findings += [(path,) + f for f in lint_statement(i, st)]
    order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    findings.sort(key=lambda f: (f[0], order[f[1]]))
    for path, sev, sid, msg in findings:
        print(f"{path}  {sev:<6} {sid:<20} {msg}")
    highs = sum(1 for f in findings if f[1] == "HIGH")
    print(f"\n{highs} high, {len(findings) - highs} other" if findings else "No over-broad statements found.")
    return 1 if highs else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
