---
name: injection-review
description: Reviews code for SQL, command, template, and XSS injection, SSRF, and path traversal by tracing input to dangerous sinks. Use for code that builds queries, shells out, or renders input.
---

# Detailed Instructions

Find every place untrusted input reaches a **sink** that interprets it — a query, a shell, a
template, an HTML page, a URL fetch, a file path — and check that the boundary is safe by
construction (parameters, argument arrays, auto-escaping, allowlists), not by a hand-written
filter. Injection bugs live in the one string concatenation nobody noticed; filters and
blocklists get bypassed, structural fixes don't.

## When to Use

- Reviewing code that builds SQL, NoSQL, LDAP, or ORM raw queries
- Code that calls `subprocess`, `exec`, `os.system`, `child_process`, or shell scripts with input
- Rendering user content in HTML, templates, emails, or Markdown
- Fetching URLs, webhooks, or images from user-supplied addresses
- Reading, writing, or unzipping files whose names come from requests

**Don't use when:** triaging a list of scanner findings (use `security-finding-triage`), reviewing
login, session, or permission logic (use `auth-code-review`), or the whole-system risk picture is
needed first (use `threat-model-lite`).

## Overview

Reviews miss injection because they read code top-down and the dangerous call looks harmless
in isolation. This skill works sink-first: list the dangerous sinks in the change, trace each one
back to its sources, decide whether untrusted data reaches it unsafely, and give the structural
fix with code. Each finding carries a severity, a one-line proof, and the fix.

## Workflow Rules

### 1. Find sinks

1. Search for sinks by class (adapt to the language):

| Class | Sinks to grep |
|---|---|
| SQL / NoSQL | `execute(`, `raw(`, `.query(` built with f-strings, `+`, `%`, template literals; `$where` or operators taken from input |
| OS command | `os.system`, `subprocess` with `shell=True`, `exec`, `child_process.exec`, backticks, `Runtime.exec` with one string |
| Code / template | `eval`, `Function(`, `render_template_string`, Jinja `from_string`, `pickle.loads`, `yaml.load` without a safe loader |
| XSS | `innerHTML`, `dangerouslySetInnerHTML`, `v-html`, `\|safe`, `mark_safe`, `html_safe` |
| SSRF | `requests.get(url)`, `fetch(url)`, `urllib`, image/PDF renderers, webhooks with user URLs |
| Path traversal | `open(base + name)`, `send_file`, `path.join(dir, input)`, zip/tar extraction |

### 2. Trace sources

2. For each sink, trace its arguments back to a source: request params, body, headers, cookies,
   uploaded file contents, database rows users wrote (stored injection), queue messages. Note any
   validation on the path.
3. A sink is **safe** when input can't change the structure: parameterized query, argument list
   without a shell, auto-escaped template, strict allowlist (enum, integer cast), resolved path
   confirmed inside the base directory. It's **unsafe** when input is concatenated or only
   filtered by a blocklist.

### 3. Fix structurally

4. Give the fix for the class:
   - **SQL:** placeholders (`cursor.execute("… WHERE id = %s", (id,))`) or ORM filters.
     Identifiers (column, sort order) can't be parameters — map them through an allowlist dict.
   - **Command:** argument arrays without a shell (`subprocess.run(["convert", src, out])`), `--`
     before user arguments, and a library instead of a shell call where one exists.
   - **Template / code:** never render user input as a template or `eval` it; use
     `yaml.safe_load`, and JSON instead of pickle.
   - **XSS:** rely on framework auto-escaping; for user HTML, sanitize with DOMPurify or nh3 using
     an allowlist; add a CSP as defense in depth.
   - **SSRF:** allowlist hosts where possible; otherwise resolve DNS, reject private, loopback,
     link-local (cloud metadata at 169.254.169.254), and reserved addresses **after**
     resolution, connect to the checked IP, and re-check every redirect.
   - **Path traversal:** generate file names server-side; otherwise
     `resolved = (base / name).resolve()` and require `resolved.is_relative_to(base.resolve())`
     (Python 3.9+); validate each member path when extracting archives.
5. Rate each finding: **Critical** (unauthenticated code execution, SQLi on sensitive data),
   **High** (authenticated code execution or SQLi, SSRF to metadata, stored XSS), **Medium**
   (reflected XSS, limited traversal), **Low** (needs unlikely conditions). Show a one-line proof
   input so the reader sees it's real — not a full exploit chain.

## Checklist

```text
- [ ] All sink classes searched in the changed code
- [ ] Each sink traced to its sources (including stored data)
- [ ] Safe-by-construction vs. filtered/concatenated decided per sink
- [ ] Identifiers (columns, sort, table names) allowlisted
- [ ] SSRF checks happen after DNS resolution and on redirects
- [ ] Path checks use resolved paths; archive members validated
- [ ] Each finding: severity, one-line proof, structural fix with code
- [ ] Defense in depth noted (CSP, least-privilege DB user, egress rules)
```

## Red Flags

- "It's only used by admins." (Admin accounts get phished; stored input reaches other users.)
- A regex or blocklist that strips `'`, `;`, `<script>`, or `../`.
- Escaping by hand instead of parameterizing.
- "The value comes from our database, so it's trusted." (Who wrote it there?)
- Checking a URL's hostname string instead of the resolved IP.

## Common Rationalizations

| Excuse | Reality |
|---|---|
| "We validate input on the frontend." | Anyone can call the API directly. |
| "The ORM protects us." | Not in `raw()`, `extra()`, `literal()`, or string-built `order_by`. |
| "We strip `<script>` tags." | Event-handler attributes, `javascript:` URLs, and SVG get past it. |
| "Internal services aren't reachable." | SSRF is exactly how they get reached, cloud metadata included. |

## Anti-Patterns (What NOT to do)

* **Recommending blocklists or escaping helpers as the main fix** — they get bypassed; fix the structure.
* **Reviewing only request handlers** — stored input from the DB, queues, and files reaches sinks too.
* **Parameterizing values but string-building identifiers** — sort columns and table names need allowlists.
* **Writing working exploit chains** — a one-line proof makes the point.
* **Flagging safe calls** (parameterized queries, `subprocess.run([...])` without a shell) — noise erodes trust in the review.

## Examples

### Example 1: a reporting endpoint

**User:** "Review this Flask endpoint."

```python
@app.get("/reports")
def reports():
    sort = request.args.get("sort", "created_at")
    q = request.args.get("q", "")
    rows = db.execute(f"SELECT * FROM reports WHERE title LIKE '%{q}%' ORDER BY {sort}")
    fmt = request.args.get("fmt", "pdf")
    os.system(f"render-report --format {fmt} /tmp/out")
    return render_template_string("<h1>Results for " + q + "</h1>", rows=rows)
```

**Expected output:**

```markdown
**1. SQL injection — Critical** (`q` and `sort` → `db.execute`)
Proof: `q='` breaks the query; a crafted `q` can read other tables.
Fix: parameterize the value; allowlist the identifier.
    SORTS = {"created_at": "created_at", "title": "title"}
    order = SORTS.get(sort, "created_at")
    rows = db.execute(
        f"SELECT * FROM reports WHERE title LIKE %s ORDER BY {order}",
        (f"%{q}%",))

**2. Command injection — Critical** (`fmt` → `os.system`)
Proof: `fmt=pdf;id` runs a second command.
Fix: allowlisted value, argument list, no shell.
    if fmt not in {"pdf", "csv"}: abort(400)
    subprocess.run(["render-report", "--format", fmt, "/tmp/out"], check=True)

**3. Server-side template injection — Critical** (`q` → `render_template_string`)
Proof: `q={{7*7}}` renders "49"; `{{ config }}` leaks app secrets.
Fix: a fixed template with input passed as data (auto-escaped):
    return render_template_string("<h1>Results for {{ q }}</h1>", q=q, rows=rows)

Defense in depth: run the app's DB user without read access to `users.password_hash`.
```

### Example 2: an SSRF check that doesn't work

**User:** "We block internal URLs like this — is it OK?"

```python
if urlparse(url).hostname in ("localhost", "127.0.0.1", "169.254.169.254"):
    abort(400)
requests.get(url)
```

**Expected output:**

```text
No — High severity. The check compares hostname strings, so other spellings and indirection pass:
- alternate encodings of loopback (e.g. http://[::1]/, http://0/)
- any DNS name that resolves to an internal address
- an allowed URL that redirects to the metadata service

Fix: resolve, check the IP, connect to that IP, and handle redirects yourself.
    ip = ipaddress.ip_address(socket.getaddrinfo(host, port)[0][4][0])
    if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
        abort(400)
    # request the checked IP (Host header = original host), allow_redirects=False,
    # and repeat the check for each redirect target.
Better still: an allowlist of webhook domains, egress rules blocking metadata IPs, and IMDSv2 on AWS.
```

## Quick Reference

| Sink | Safe pattern |
|---|---|
| SQL value | Placeholders / ORM filters |
| SQL identifier | Allowlist dict |
| Shell | Argument array, no shell, `--` before user args |
| Templates | Fixed template, input as context |
| HTML | Auto-escape; DOMPurify/nh3 for rich text; CSP |
| URL fetch | Allowlist, or resolve → block internal IPs → pin → recheck redirects |
| File path | Server-generated names, or resolved path inside base |
| Deserialize | JSON, `yaml.safe_load`; never `pickle` on input |
