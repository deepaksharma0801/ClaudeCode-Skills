#!/usr/bin/env python3
"""Grade a site's HTTP security headers and cookies. Standard library only (Python 3.8+).

Usage:
    python3 check_headers.py https://example.com            # fetch live (GET, follows redirects)
    python3 check_headers.py --headers-file headers.txt      # offline: output of `curl -sI URL`
    python3 check_headers.py https://example.com --json

Exit code: 1 if any HIGH finding, else 0. Only sends ordinary GET requests (plus one to the
http:// version to check the HTTPS redirect) — no probing or payloads.
Guidance follows the OWASP Secure Headers Project and MDN.
"""
import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from urllib.parse import urlsplit, urlunsplit

HSTS_MIN = 31536000  # one year
GOOD_REFERRER = {"no-referrer", "same-origin", "strict-origin", "strict-origin-when-cross-origin"}


class Headers:
    """Case-insensitive multi-valued header store."""

    def __init__(self, pairs):
        self.items = [(k.strip().lower(), v.strip()) for k, v in pairs]

    def get(self, name):
        values = [v for k, v in self.items if k == name]
        return ", ".join(values) if values else None

    def all(self, name):
        return [v for k, v in self.items if k == name]


def parse_header_text(text):
    """Parse `curl -sI` output; keep only the last response block (after redirects)."""
    blocks, current = [], []
    for line in text.splitlines():
        if line.upper().startswith("HTTP/"):
            current = []
            blocks.append(current)
        elif ":" in line and blocks:
            k, v = line.split(":", 1)
            current.append((k, v))
    if not blocks:
        raise SystemExit("error: no 'HTTP/' status line found; save headers with `curl -sI URL > headers.txt`")
    return Headers(blocks[-1])


def fetch(url, timeout):
    req = urllib.request.Request(url, headers={"User-Agent": "security-headers-check/1.0"})
    try:
        resp = urllib.request.urlopen(req, timeout=timeout)
    except urllib.error.HTTPError as err:  # 4xx/5xx still carry headers
        resp = err
    except (urllib.error.URLError, OSError) as err:
        raise SystemExit(f"error: could not fetch {url}: {err}")
    return resp.geturl(), Headers(resp.headers.items())


def https_redirect(url, timeout):
    parts = urlsplit(url)
    if parts.scheme != "https":
        return None
    http_url = urlunsplit(("http",) + tuple(parts[1:]))
    try:
        final, _ = fetch(http_url, timeout)
    except SystemExit:
        return None  # port 80 closed is fine
    return final.startswith("https://")


def csp_directives(csp):
    out = {}
    for part in csp.split(";"):
        tokens = part.strip().split()
        if tokens:
            out.setdefault(tokens[0].lower(), [t.lower() for t in tokens[1:]])
    return out


def grade(h, final_url, redirect_ok):
    f = []  # (severity, header, message)
    add = lambda sev, hdr, msg: f.append((sev, hdr, msg))
    is_https = final_url is None or final_url.startswith("https://")

    if redirect_ok is False:
        add("HIGH", "redirect", "http:// does not redirect to https://")
    if not is_https:
        add("HIGH", "transport", "page is served over plain HTTP")

    hsts = h.get("strict-transport-security")
    if is_https:
        if not hsts:
            add("HIGH", "Strict-Transport-Security", "missing; browsers may connect over HTTP first")
        else:
            m = re.search(r"max-age\s*=\s*\"?(\d+)", hsts, re.I)
            age = int(m.group(1)) if m else 0
            if age < HSTS_MIN:
                add("MEDIUM", "Strict-Transport-Security", f"max-age={age}; use at least {HSTS_MIN} (1 year)")
            if "includesubdomains" not in hsts.lower():
                add("LOW", "Strict-Transport-Security", "no includeSubDomains")

    csp = h.get("content-security-policy")
    d = csp_directives(csp) if csp else {}
    if not csp:
        ro = " (only Report-Only is set)" if h.get("content-security-policy-report-only") else ""
        add("HIGH", "Content-Security-Policy", f"missing{ro}; no defense in depth against XSS")
    else:
        scripts = d.get("script-src", d.get("default-src"))
        if scripts is None:
            add("HIGH", "Content-Security-Policy", "no script-src or default-src; scripts are unrestricted")
        else:
            has_nonce = any(t.startswith(("'nonce-", "'sha256-", "'sha384-", "'sha512-")) for t in scripts)
            if "'unsafe-inline'" in scripts and not has_nonce:
                add("HIGH", "Content-Security-Policy", "script-src allows 'unsafe-inline' without nonces/hashes")
            if "'unsafe-eval'" in scripts:
                add("MEDIUM", "Content-Security-Policy", "script-src allows 'unsafe-eval'")
            if any(t in ("*", "http:", "https:", "data:") for t in scripts):
                add("HIGH", "Content-Security-Policy", "script-src allows any host or data: URLs")
        if "object-src" not in d and d.get("default-src") != ["'none'"]:
            add("LOW", "Content-Security-Policy", "no object-src 'none'")
        if "base-uri" not in d:
            add("LOW", "Content-Security-Policy", "no base-uri (e.g. base-uri 'none' or 'self')")

    xfo = (h.get("x-frame-options") or "").lower()
    if "frame-ancestors" not in d and xfo not in ("deny", "sameorigin"):
        add("MEDIUM", "Framing", "no CSP frame-ancestors or X-Frame-Options; page can be framed (clickjacking)")

    if (h.get("x-content-type-options") or "").lower() != "nosniff":
        add("MEDIUM", "X-Content-Type-Options", "should be 'nosniff'")

    ref = (h.get("referrer-policy") or "").lower()
    ref_last = ref.split(",")[-1].strip() if ref else ""
    if not ref:
        add("LOW", "Referrer-Policy", "missing; set strict-origin-when-cross-origin or stricter")
    elif ref_last not in GOOD_REFERRER:
        add("MEDIUM", "Referrer-Policy", f"'{ref_last}' can leak full URLs to other sites")

    if not h.get("permissions-policy"):
        add("LOW", "Permissions-Policy", "missing; disable features you don't use (camera, geolocation, ...)")

    xxp = (h.get("x-xss-protection") or "").replace(" ", "")
    if xxp and xxp != "0":
        add("LOW", "X-XSS-Protection", f"'{xxp}' enables the legacy XSS auditor; set 0 or remove, rely on CSP")

    acao = h.get("access-control-allow-origin")
    if acao == "*" and (h.get("access-control-allow-credentials") or "").lower() == "true":
        add("HIGH", "CORS", "Allow-Origin * with Allow-Credentials true (misconfigured; check origin handling)")

    for name in ("server", "x-powered-by", "x-aspnet-version"):
        v = h.get(name)
        if v and (name != "server" or re.search(r"\d", v)):
            add("LOW", name.title(), f"reveals software: '{v}'")

    for cookie in h.all("set-cookie"):
        cname = cookie.split("=", 1)[0].strip()
        attrs = [a.strip().lower() for a in cookie.split(";")[1:]]
        missing = [a for a in ("secure", "httponly") if a not in attrs]
        if not any(a.startswith("samesite") for a in attrs):
            missing.append("SameSite")
        if missing:
            sev = "MEDIUM" if "secure" in missing and is_https else "LOW"
            label = {"secure": "Secure", "httponly": "HttpOnly", "SameSite": "SameSite"}
            add(sev, f"Set-Cookie {cname}", "missing " + ", ".join(label[m] for m in missing))
    return f


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("url", nargs="?")
    ap.add_argument("--headers-file", help="raw headers from `curl -sI URL` (offline mode)")
    ap.add_argument("--timeout", type=float, default=10)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    if not args.url and not args.headers_file:
        ap.error("give a URL or --headers-file")

    if args.headers_file:
        with open(args.headers_file, encoding="utf-8", errors="replace") as fh:
            h = parse_header_text(fh.read())
        final_url, redirect_ok = args.url, None
    else:
        final_url, h = fetch(args.url, args.timeout)
        redirect_ok = https_redirect(args.url, args.timeout)

    findings = grade(h, final_url, redirect_ok)
    order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    findings.sort(key=lambda x: order[x[0]])
    if args.json:
        print(json.dumps({"url": final_url, "findings": [dict(zip(("severity", "header", "message"), x)) for x in findings]}, indent=2))
    else:
        print(f"Checked: {final_url or args.headers_file}")
        for sev, hdr, msg in findings:
            print(f"  {sev:<6} {hdr:<28} {msg}")
        counts = {s: sum(1 for x in findings if x[0] == s) for s in order}
        print(f"\n{counts['HIGH']} high, {counts['MEDIUM']} medium, {counts['LOW']} low" if findings else "No issues found.")
    return 1 if any(x[0] == "HIGH" for x in findings) else 0


if __name__ == "__main__":
    sys.exit(main())
