---
name: kubernetes-manifest-review
description: Reviews Kubernetes manifests and Helm charts for security context, resource limits, probes, secrets handling, RBAC, and network policy. Use when reviewing k8s YAML, Helm values, or a deployment PR.
compatibility: Uses kubectl and optionally kube-linter, kubeconform, or Trivy if installed.
---

# Detailed Instructions

Review every workload against two questions: **if this container is compromised, how far can
an attacker get?** (security context, service account, RBAC, network policy, secrets), and
**will it stay up and avoid taking its neighbors down?** (requests, limits, probes, disruption
budgets). Most Kubernetes incidents and breaches trace back to defaults nobody overrode:
running as root, the auto-mounted service account token, no resource limits, and no
network policy.

## When to Use

- Reviewing a PR that adds or changes Deployments, StatefulSets, CronJobs, Services, Ingress,
  RBAC, or Helm values
- "Is this manifest production-ready?"
- Hardening an existing namespace before an audit
- Debugging OOMKilled, CrashLoopBackOff, or pods evicted under load (as a config review)

**Don't use when:** the issue is the image itself (use `dockerfile-optimizer` and
`dependency-audit`), or cloud IAM for the cluster (use `iam-policy-review`).

## Overview

Kubernetes defaults favor "it runs" over "it's safe": containers run as root with a writable
root filesystem, every pod gets a service account token, pods can talk to any other pod, and
unlimited pods can starve a node. This skill runs available linters, then checks each workload
against a fixed list grouped by security, reliability, and operability, and gives the YAML to
fix each finding.

## Workflow Rules

### 1. Render and lint

1. Render Helm charts first (`helm template . -f values-prod.yaml`) — review what will actually
   be applied. Validate schemas with `kubeconform -strict` and run `kube-linter lint` or
   `trivy config` if installed; merge their findings.

### 2. Security (per container and pod)

2. `securityContext`: `runAsNonRoot: true`, `allowPrivilegeEscalation: false`,
   `readOnlyRootFilesystem: true` (with `emptyDir` for writable paths),
   `capabilities: { drop: ["ALL"] }`, `seccompProfile: { type: RuntimeDefault }`.
   Flag `privileged: true`, `hostNetwork`, `hostPID`, `hostPath` mounts.
3. Service account: a dedicated one per app; `automountServiceAccountToken: false` unless the app
   calls the API server.
4. RBAC: no `cluster-admin` bindings for apps; no `*` verbs or resources; Roles over
   ClusterRoles; watch for `secrets` get/list, `pods/exec`, and `create` on workloads — each
   lets someone escalate.
5. Secrets: never in plain `env.value` or ConfigMaps; reference Secrets (ideally from an
   external secret manager via External Secrets or CSI). Remember Secrets are only base64-encoded
   unless encryption at rest is enabled.
6. NetworkPolicy: a default-deny in the namespace, then explicit allows for required ingress and
   egress.
7. Images: pinned by tag **and** digest or at least an immutable tag — never `:latest`; private
   registry with `imagePullPolicy` that fits.

### 3. Reliability

8. **Requests** for CPU and memory on every container (scheduling depends on them); **memory
   limit** set (OOM protection); CPU limits are optional and can cause throttling — note the team's
   policy.
9. **Probes:** `readinessProbe` (traffic only when ready), `livenessProbe` that checks the process
   itself, not dependencies (otherwise a DB blip restarts everything), `startupProbe` for slow
   starts.
10. `replicas ≥ 2` for anything user-facing, a `PodDisruptionBudget`, and topology spread or
    anti-affinity across nodes/zones.
11. Graceful shutdown: `terminationGracePeriodSeconds` longer than the longest request; a
    `preStop` sleep if the load balancer needs time to deregister.

### 4. Report

12. Group findings by severity: **Critical** (privileged, cluster-admin, secrets in plain text),
    **High** (root, no NetworkPolicy, no memory limits, token auto-mounted with broad RBAC),
    **Medium** (missing probes, single replica), **Low** (labels, annotations). Give the YAML patch.

## Checklist

```text
- [ ] Helm rendered; kubeconform / kube-linter / trivy run if available
- [ ] Non-root, no privilege escalation, read-only rootfs, drop ALL, seccomp
- [ ] No privileged/hostNetwork/hostPID/hostPath
- [ ] Dedicated service account; token not mounted unless needed
- [ ] RBAC scoped; no secrets list, pods/exec, or wildcards for apps
- [ ] Secrets referenced, not inlined
- [ ] Default-deny NetworkPolicy + explicit allows
- [ ] Image pinned; not :latest
- [ ] Requests + memory limits; probes correct; replicas ≥ 2 + PDB
- [ ] Graceful shutdown configured
```

## Red Flags

- `image: myapp:latest`
- `privileged: true` "because it didn't work otherwise".
- A liveness probe that calls the database.
- `kind: ClusterRoleBinding` to `cluster-admin` for an app's service account.
- `env: - name: DB_PASSWORD value: "…"`

## Common Rationalizations

| Excuse | Reality |
|---|---|
| "The cluster is private." | A single compromised pod can reach everything without NetworkPolicy. |
| "Secrets are encrypted in Kubernetes." | Only base64 unless encryption at rest is configured, and readable by anyone with get on secrets. |
| "Limits cause OOMs." | Without memory limits, one leaking pod gets the whole node evicted. |
| "Running as root is required." | Usually only for binding low ports or writing to the image; fix those instead. |

## Anti-Patterns (What NOT to do)

* **Reviewing Helm templates without rendering them** — values change the outcome.
* **Liveness probes that check dependencies** — cascading restarts during a dependency blip.
* **Wildcard RBAC for convenience** — turns any pod compromise into cluster compromise.
* **`:latest` tags** — unreproducible deploys and silent changes.
* **Copying a hardened context without `emptyDir` for writable paths** — the app crashes and someone reverts all hardening.

## Examples

### Example 1: a typical deployment

**User:** "Review this."

```yaml
apiVersion: apps/v1
kind: Deployment
metadata: { name: api }
spec:
  replicas: 1
  template:
    spec:
      containers:
        - name: api
          image: registry.example.com/api:latest
          env:
            - { name: DATABASE_URL, value: "postgres://app:S3cret@db:5432/app" }
          livenessProbe:
            httpGet: { path: /health/db, port: 8080 }
```

**Expected output:**

```markdown
**Critical** — DB password inline in `env.value`. Move to a Secret (from your secret manager):
    envFrom: [{ secretRef: { name: api-db } }]
Rotate this password: it's now in git history.

**High** — No securityContext (runs as image default, likely root). Add:
    securityContext:
      runAsNonRoot: true
      allowPrivilegeEscalation: false
      readOnlyRootFilesystem: true
      capabilities: { drop: ["ALL"] }
      seccompProfile: { type: RuntimeDefault }
**High** — No resources. Add requests (e.g. cpu 250m, memory 256Mi) and a memory limit (512Mi),
tuned from current usage (`kubectl top pods`).
**High** — `:latest` image. Pin a version tag or digest.

**Medium** — Liveness checks the database: a DB blip restarts every pod. Point liveness at
`/health/live` (process only) and use `/health/ready` (incl. DB) for readiness.
**Medium** — 1 replica, no PDB: every deploy or node drain is downtime. Use 2+ replicas and
`PodDisruptionBudget` with `minAvailable: 1`.
**Medium** — Service account token auto-mounted; set `automountServiceAccountToken: false`.
Also check the namespace has a default-deny NetworkPolicy.
```

### Example 2: an RBAC role

**User:** "Our CI deployer has this Role: verbs ["*"], resources ["*"] in the prod namespace."

**Expected output:**

```text
High. "*" on "*" in prod includes reading every Secret and `pods/exec` into any pod — CI
compromise becomes full prod access. Scope it to what deploys need:
  - apiGroups: ["apps"]; resources: ["deployments"]; verbs: ["get","list","patch","update"]
  - apiGroups: [""]; resources: ["services","configmaps"]; verbs: ["get","list","patch","update","create"]
Leave secrets out (have External Secrets sync them), and use short-lived OIDC credentials for
the CI identity rather than a long-lived token.
```

## Quick Reference

| Area | Safe default |
|---|---|
| securityContext | nonRoot, no escalation, read-only rootfs, drop ALL, seccomp |
| Service account | Dedicated; token off unless needed |
| RBAC | Namespaced, explicit verbs/resources, no secrets/exec |
| Secrets | Referenced from Secret / external manager |
| Network | Default-deny + explicit allows |
| Image | Pinned tag or digest |
| Resources | Requests + memory limit |
| Probes | Liveness = process; readiness = dependencies |
| Availability | ≥ 2 replicas, PDB, spread across zones |
