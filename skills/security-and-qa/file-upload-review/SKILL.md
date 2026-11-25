---
name: file-upload-review
description: Reviews file upload handling for type spoofing, path traversal, stored XSS, oversized files, malware, and public bucket exposure. Use when code accepts uploads, avatars, imports, or attachments.
---

# Detailed Instructions

Treat every uploaded file as hostile: its name, its claimed type, its size, and its contents
are all attacker-controlled. Safe upload handling comes from a few structural choices: generate
the storage name yourself, check the real content type against an allowlist, cap the size
before reading the whole body, store outside the web root (or in a private bucket), and serve
it back with headers that stop the browser from executing it. Most upload vulnerabilities
come from trusting one of those attacker-controlled properties.

## When to Use

- Code that accepts uploads: avatars, documents, CSV/Excel imports, attachments, media
- Presigned-URL flows to S3, GCS, or Azure Blob
- Image or document processing pipelines (thumbnails, PDF rendering, unzip)
- Reviewing how uploaded files are served back to users

**Don't use when:** the main risk is generic injection elsewhere in the code (use
`injection-review`), or the issue is bucket IAM policy in general (use `iam-policy-review`).

## Overview

Upload bugs range from defacement to remote code execution: an `.php` file saved into a served
directory, an SVG with script served inline from the main domain, a `../../` filename, a
zip that expands to 10 GB, an ImageMagick parser exploit, or a bucket that's public. This skill
walks the upload's lifecycle — receive, validate, store, process, serve — and checks each stage
against a fixed list, giving the fix in code or config.

## Workflow Rules

Walk the lifecycle in order and record a finding per failed check.

### 1. Receive

1. **Size limit before buffering:** enforce at the proxy/framework (`client_max_body_size`,
   `MAX_CONTENT_LENGTH`, multer `limits.fileSize`) so huge uploads are rejected early, not after
   being read into memory.
2. **Rate and count limits** per user to stop storage-filling abuse.
3. **Authentication and authorization** on the upload endpoint, and on presigned-URL issuance.

### 2. Validate

4. **Allowlist types by content, not by name or header.** Check magic bytes (python-magic,
   `file-type` in Node) and the extension against a short allowlist; the `Content-Type` header
   and the filename are client-supplied.
5. **Never trust the filename:** generate a random storage key (UUID); keep the original name
   only as metadata, sanitized for display.
6. **Archives:** limit total uncompressed size and file count; reject entries with `..`,
   absolute paths, or symlinks (zip slip).
7. **Spreadsheets/CSV that will be exported again:** escape cells starting with `=`, `+`, `-`,
   `@` (CSV injection).

### 3. Store

8. Store outside the web root, or in a **private** bucket with Block Public Access on. Never in a
   directory the app server executes.
9. Presigned uploads: short expiry, fixed key chosen by the server, and `content-length-range`
   and content-type conditions in the POST policy.

### 4. Process

10. Run parsers (ImageMagick, LibreOffice, ffmpeg, PDF renderers) in an isolated worker with
    timeouts and memory limits; keep them patched. Re-encode images to strip metadata and
    embedded payloads (and EXIF location data — a privacy issue too).
11. Scan for malware (ClamAV or the cloud provider's scanning service) where files are shared
    with other users.

### 5. Serve

12. Serve user files from a **separate domain** (e.g. `usercontent.example.net`) or via signed
    URLs, so a malicious HTML/SVG can't run with the main site's cookies.
13. Set `Content-Disposition: attachment` for anything not meant to display inline,
    `X-Content-Type-Options: nosniff`, and the stored, validated `Content-Type`. SVG and HTML
    are never served inline from the main origin.
14. Check access on download: object-level authorization, not guessable sequential ids.

## Checklist

```text
- [ ] Size limit enforced before buffering; rate limits per user
- [ ] Upload and presign endpoints authenticated and authorized
- [ ] Type checked by magic bytes against an allowlist
- [ ] Storage name generated server-side; original name sanitized metadata
- [ ] Archives: size/count limits, no traversal or symlinks
- [ ] Private storage outside web root; Block Public Access on
- [ ] Presigned URLs short-lived with size/type conditions
- [ ] Parsers isolated with limits; images re-encoded; malware scan if shared
- [ ] Served from a separate domain or signed URL; nosniff; attachment for non-media
- [ ] Download authorization per object
```

## Red Flags

- `file.save(os.path.join(UPLOAD_DIR, file.filename))`
- Checking `file.content_type == "image/png"` and nothing else.
- Uploads under `/static` or `/public` on the app's own domain.
- `ACL: public-read` on uploaded objects.
- Unzipping uploads without checking entry paths or total size.

## Common Rationalizations

| Excuse | Reality |
|---|---|
| "We check the extension." | `avatar.png` can contain HTML or a polyglot; check content and serve safely. |
| "Only images are allowed." | SVG is an image and runs script when served inline. |
| "The bucket URLs are unguessable." | They leak via logs, referrers, and shares; use private buckets + signed URLs. |
| "Our users are trusted employees." | Accounts get compromised; uploads reach other users. |

## Anti-Patterns (What NOT to do)

* **Using the client's filename as the path** — path traversal and overwrites.
* **Blocklisting bad extensions** (`.php`, `.exe`) — there's always one more; allowlist instead.
* **Serving user HTML/SVG inline from the main domain** — stored XSS with session cookies.
* **Processing files in the web process with no limits** — one malicious file takes down the app.
* **Public-read buckets for private documents** — a single URL leak exposes the file.

## Examples

### Example 1: an avatar endpoint

**User:** "Review this Flask upload."

```python
@app.post("/avatar")
@login_required
def avatar():
    f = request.files["file"]
    if not f.filename.endswith((".png", ".jpg", ".svg")):
        abort(400)
    f.save(os.path.join("static/avatars", f.filename))
    return {"url": f"/static/avatars/{f.filename}"}
```

**Expected output:**

```markdown
**1. Path traversal / overwrite — High.** `f.filename` is used as the path; a name like
`../templates/base.html` (some clients send it unsanitized) or another user's avatar name
overwrites files. Fix: `key = f"{uuid4()}.{ext}"`.

**2. Stored XSS — High.** `.svg` is allowed and served inline from the main origin under
/static. Fix: drop SVG (or rasterize it), and serve avatars from a separate domain or with
`nosniff` and the validated type.

**3. Type check by name only — Medium.** Fix: check magic bytes and re-encode:
    img = Image.open(f.stream); img.verify()          # Pillow
    f.stream.seek(0); img = Image.open(f.stream)
    if img.format not in {"PNG", "JPEG"}: abort(400)
    img.thumbnail((512, 512)); img.save(buf, format="PNG")   # strips metadata

**4. No size limit — Medium.** Set `app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024`.

**5. Storage in the app's static dir — Medium.** Move to a private bucket; return a signed URL or
serve via a CDN on a separate domain.
```

### Example 2: presigned S3 uploads

**User:** "We generate a presigned PUT URL with the client's filename as the key, valid 7 days."

**Expected output:**

```text
Three fixes:
1. Key: the client chooses the object key → it can overwrite other users' files. Generate it on
   the server: uploads/{user_id}/{uuid4()}.
2. Expiry: 7 days is far too long for a URL that grants write access. Use 5–15 minutes.
3. No size/type control: a presigned PUT can't enforce size. Switch to a presigned POST with a
   policy: ["content-length-range", 1, 10485760] and a Content-Type condition, then verify the
   object's real type after upload (S3 event → validation worker) before marking it usable.
Also confirm Block Public Access is on for the bucket.
```

## Quick Reference

| Stage | Safe default |
|---|---|
| Receive | Size cap at proxy/framework; auth; rate limit |
| Validate | Magic bytes + extension allowlist |
| Name | Server-generated UUID key |
| Archives | Size/count caps; reject `..`, absolute, symlinks |
| Store | Private bucket, outside web root |
| Process | Isolated worker, limits, re-encode, malware scan |
| Serve | Separate domain or signed URL; `nosniff`; `attachment` |
