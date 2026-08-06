# Onboarding & Access Management

> **Status: DOC/PREP ONLY (master_todo #60).** This document is the design +
> runbook for letting one or more *additional* people (e.g. the user's
> financial advisor) receive digests/alerts and/or view the tool, with
> minimal added complexity. **No code has shipped for this yet.** The
> "Design" sections below describe exactly what a future code cycle would
> change and where; the "Runbook" sections describe what is possible *today*
> with the shipped code + infra.
>
> Companion docs: `docs/Project_State.md` (canonical state), `docs/data_flow.md`
> (notification paths), `docs/self_hosting.md` (#61, standing up a fresh
> instance), and both repo READMEs.

The system has two access surfaces a second person could want:

1. **Notifications** — receive the weekly digest email + (optionally) the
   drift/alert emails. This is the low-complexity, high-value path.
2. **The web UI** — view the dashboard/holdings/suggestions in a browser.
   This requires network access (Tailscale) because there is no public
   ingress and no per-user auth.

Treat these independently: a person can be added to email without any UI
access, and vice versa.

---

## Design constraint that shapes everything

This is a **single-user system by design** (Project_State §1, §21). There is:

- **No multi-user model.** `user_profile` has exactly one doc (`_id: "sahil"`,
  seeded from `RESEND_TO` in `scripts/init_db.py`). Holdings, transactions,
  feedback, and suggestions are all "the user's" — there is no per-recipient
  scoping.
- **No auth layer.** `middleware.ts` does not exist in the frontend; the
  backend has no login. **Tailscale is the entire auth perimeter** (frontend
  README §11 gotcha 7). Anyone on the tailnet who can reach `:3000`/`:8000`
  sees *everything*.

**Consequence:** adding a second *viewer* means giving them read access to the
author's real portfolio. That is a trust decision, not a technical toggle.
Adding a second *email recipient* is lower-stakes (they see only what the
digest/alert contains) but still exposes portfolio figures. Multi-user
isolation is explicitly out of scope (§21) and nothing here changes that.

---

## Part A — Multi-recipient email (#60 core)

### Current shipped behavior (verified at backend HEAD)

- `settings.RESEND_TO` is a **single** `str` (`app/config/settings.py`).
- `notify.email(subject, html, to=None, text=None)` defaults `to` to
  `settings.RESEND_TO` (`app/services/notify.py`). It returns
  `{ok, id, error}` and never raises (the A2 wrapper contract).
- The two email senders both call `notify.email()` **without** a `to=`
  argument, so both go to `RESEND_TO` only:
  - `digest_delivery._send_email(subject, html, text)` — the weekly digest.
  - `reconciliation._send_drift_alerts(...)` — the manual reconciliation
    drift email. (The daily auto-drift path `_send_auto_drift_alert` is
    **ntfy-only by design** — no email — so it is not a recipient surface.)
- `cron_health_check.py` also emails via `notify.email()` (dual-transport
  anomaly + #66 positive daily heartbeat), again to `RESEND_TO` only.

So **today** there is exactly one email recipient, set by the `RESEND_TO`
secret, and no code path passes a different/additional address.

### What Resend supports (no new dependency needed)

Resend's `Emails.send` accepts `to` as **either a string or a list of
strings** (up to 50 recipients per send). So multi-recipient is achievable
without any new library — it is purely a matter of how we source and pass the
recipient list. Two options for *who sees whom*:

- **`to` list** — all recipients see each other in the To: header.
- **`bcc` list** — recipients are hidden from each other. For a personal tool
  where the advisor and the author both know they're on it, `to` is fine and
  simpler; `bcc` is the privacy-preserving choice if recipients should not
  see each other.

### Proposed design (for a future code cycle — NOT yet built)

Minimal, evolves the existing single wrapper; introduces **no** parallel
notification path (honors the "don't invent parallel patterns" rule).

1. **Settings — add an optional CC/extra-recipients list.**
   Add to `app/config/settings.py`:
   ```python
   # Optional additional digest/alert recipients (comma-separated in the
   # secrets file). RESEND_TO stays the single PRIMARY recipient so the
   # user_profile seed + all existing behavior is byte-unchanged when unset.
   RESEND_CC: str = ""   # e.g. "advisor@example.com,spouse@example.com"
   ```
   Keeping `RESEND_TO` as the single primary preserves the
   `init_db.seed_user_profile()` derivation (`RESEND_TO.split("@")[0]`) with
   **zero** change — the extra recipients are additive only.

2. **notify.email — accept and merge the extra recipients.**
   Extend the wrapper so it builds the recipient list from
   `to or settings.RESEND_TO` **plus** the parsed `settings.RESEND_CC`,
   de-duplicated, empty entries stripped. Decide `to` vs `bcc` here (recommend
   `bcc` for the extras so the advisor isn't exposed to other recipients).
   The `{ok, id, error}` contract and no-raise guarantee stay identical, so
   `digest_delivery`, `reconciliation`, and `cron_health_check` need **no**
   change — they already branch only on `result["ok"]`.

3. **Per-message opt-out (optional refinement).**
   Not every email should fan out. The **weekly digest** and **reconciliation
   drift** emails are reasonable to share with an advisor; the **cron-health**
   emails are operator noise and should stay author-only. If that distinction
   is wanted, add a boolean like `include_cc: bool = True` to `notify.email()`
   and pass `include_cc=False` from `cron_health_check.py`. Default `True`
   keeps the change small.

4. **No frontend change.** Email recipients are a backend/secrets concern.

### Recipient-management runbook (what to do TODAY, once code ships)

Until the above ships, the only lever is `RESEND_TO` (single recipient). Once
`RESEND_CC` ships, the flow is:

```bash
# On EC2 — edit the secrets file (root-owned, mode 0640)
ssh ubuntu@100.112.20.41
sudo vim /etc/portfolio-advisor/secrets.env
#   RESEND_CC=advisor@example.com,spouse@example.com   # add/edit this line
sudo systemctl restart portfolio-advisor
curl -sS http://localhost:8000/health          # ok/ok
# Mirror the same edit into the Mac .env for dev symmetry.
```

Removing a recipient = delete them from the `RESEND_CC` line and restart. No
DB change; recipients are not stored in Mongo.

**Verify a real send** without waiting for Sunday:
```bash
ssh ubuntu@100.112.20.41
cd /home/ubuntu/ai-stock-advisor-backend
PYTHONPATH=. /home/ubuntu/.local/bin/uv run python scripts/run_weekly_suggestions.py \
  --direction=both          # sends the real digest to RESEND_TO (+ RESEND_CC once shipped)
#   add --no-notify for a silent rerun that skips email+ntfy entirely.
```

### Deliverability note

Resend requires the `RESEND_FROM` domain to be verified (SPF/DKIM). Adding a
new *recipient* domain needs nothing — only the *sending* domain is verified.
So an advisor on any email provider works out of the box.

---

## Part B — Tailscale access for a second viewer (#60 core)

Giving someone the **web UI** means putting them on the tailnet and pointing
them at the EC2 frontend. Because Tailscale is the auth perimeter, this grants
full read access to the live portfolio — treat it as such.

### Concepts

- The EC2 box is a tailnet node (`100.112.20.41`) running frontend `:3000`
  and backend `:8000`. There is **no public ingress**.
- A second person needs (a) to be on the tailnet, and (b) network permission
  (ACL) to reach the EC2 node's ports.

### Two ways to add a viewer

**Option 1 — Invite them as a tailnet member (they run Tailscale).**
Best when the advisor is technical / willing to install Tailscale.
1. Tailscale admin console → **Users** → **Invite external users** (share an
   invite link, or add them to your tailnet). External users can be added
   without them joining your Google/identity org.
2. They install the Tailscale client and accept the invite.
3. Restrict them to *only* the EC2 node's web ports via an ACL grant (see
   below) — do **not** give them access to your whole tailnet.
4. They browse to `http://100.112.20.41:3000`.

**Option 2 — Share a single node with them (Tailscale "node sharing").**
Best when you want to expose *only* the EC2 box, nothing else on your tailnet.
1. Admin console → **Machines** → the EC2 node → **Share…** → generate a
   share link for that node.
2. They accept into their own tailnet; they can reach *only* that shared node.
   This is the tightest blast radius.

Prefer **Option 2** for an advisor: it structurally limits them to the one
machine, so even an over-broad ACL can't leak the rest of your tailnet.

### ACL design (least privilege)

Model the extra viewer as a tagged principal that can reach *only* the two web
ports on the EC2 node — never SSH, never Mongo, never anything else. Sketch of
the tailnet policy (Tailscale ACL JSON — apply in the admin console, this is a
*design sketch*, adjust to your tailnet's tags/users):

```jsonc
{
  "tagOwners": {
    "tag:advisor-viewer": ["autogroup:admin"],
    "tag:advisor-app":    ["autogroup:admin"]   // tag applied to the EC2 node
  },
  "acls": [
    // Advisor can ONLY reach the frontend + backend web ports on the app node.
    {
      "action": "accept",
      "src":    ["tag:advisor-viewer"],
      "dst":    ["tag:advisor-app:3000", "tag:advisor-app:8000"]
    }
    // NOTE: no SSH (:22), no Mongo, no other nodes. The advisor is boxed in.
  ],
  "ssh": []   // advisor gets NO Tailscale SSH grant
}
```

Apply `tag:advisor-app` to the EC2 machine (Machines → node → Edit ACL tags)
and `tag:advisor-viewer` to the shared/invited user. With Option 2 (node
sharing) the share itself already limits reach to the one node; the ACL is
defense-in-depth.

### CORS / API reachability caveat

The backend `CORSMiddleware` and the frontend `NEXT_PUBLIC_API_BASE_URL` are
configured for same-box/tailnet use (`http://100.112.20.41:8000`). A shared
viewer hitting `http://100.112.20.41:3000` in a browser will have that browser
call the backend at whatever `NEXT_PUBLIC_API_BASE_URL` the **build** baked in.
Since the frontend build points at the EC2 backend over the tailnet, a viewer
on the tailnet resolves it fine. No CORS change is needed as long as the
viewer reaches the app via the same tailnet IP the build targets. **Do not**
add the advisor's laptop origin to CORS or expose `:8000` publicly — that would
puncture the perimeter.

### Revoking a viewer

- **Option 1 (member):** admin console → Users → remove/suspend the user, or
  delete their device.
- **Option 2 (shared node):** admin console → Machines → EC2 node → Sharing →
  revoke the share.
- Then remove the `tag:advisor-viewer` grant from the ACL. Access drops
  immediately; nothing in Mongo or the app needs touching.

---

## Part C — Decision matrix

| Want to give the advisor… | Do this | Blast radius | Code needed |
|---|---|---|---|
| Weekly digest email only | Add to `RESEND_CC` (once shipped) | Sees digest contents | Small (Part A design) |
| Digest + drift alert emails | `RESEND_CC` + include on reconciliation email | Sees portfolio deltas | Small (Part A design) |
| Full web UI (read-only view of everything) | Tailscale node-share (Option 2) + least-priv ACL | Sees the entire live portfolio | **None** (infra only) |
| Nothing operator-ish (crons/health) | Leave `include_cc=False` on health emails | — | Part A step 3 |

---

## Part D — What this doc deliberately does NOT do

- **No per-recipient data scoping / multi-tenant.** Out of scope (§21). A
  viewer sees the author's real data; that is the accepted model.
- **No auth / login.** Tailscale remains the only perimeter.
- **No public ingress, no Funnel.** Never expose `:3000`/`:8000` publicly.
- **No code shipped this cycle.** This is #60's DOC/PREP deliverable. When the
  Part A code is taken up, it becomes its own master_todo unit with tests +
  the standard deploy/verify block.
