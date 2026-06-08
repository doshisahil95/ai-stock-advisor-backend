
# Master Todo — Personal AI Stock Advisor

This file is the canonical, ordered, end-to-end task list to reach product completion. It is the source of truth for what to do next. Every new chat reads it after `Project_State.md`.

**Created:** 2026-05-29 (Chat 5.8 — review + planning)
**Last updated:** 2026-06-08 (Chat 5.13 — Phase 5 closed)
**Audit baseline:** Backend SHA `c6b1437b90c9555ab9090657af74ab550cf6e1cd`, Frontend SHA `4f31b49b103f92ea5b4721f9728156041e908f49`
**Current backend SHA (Chat 5.13 close):** deployed code HEAD `090d96c0042e7d5ccd154dcaf6329a0bba57ebb7` (Phase 5 TD29 dead-import, TD31 ISIN pattern, TD32 regex `$options` drop shipped on three backend code commits; HEAD advances after the Chat 5.13 doc commit). **Current frontend SHA (Chat 5.13 close):** `f59958015b8b07b6e84e3add7b4a302d32b43490` (Phase 5 TD28 refetchQueries swap shipped on one frontend commit). Chat 5.13 opened at backend `07d9a413b39d330e3ea9047dec4e38917a446449` (the Chat 5.12 doc commit) and frontend `4f31b49b103f92ea5b4721f9728156041e908f49`.

> Note (Chat 5.9): the on-disk copy of this file had the "Ordering rationale" + "When you finish an item…" paragraph duplicated 8 times (a paste/commit artifact). The Chat 5.9 full-file replacement collapsed it back to a single copy. No item rows were affected.

---

## Current position

**Next item to start: #19 (P2-5 / Phase 6 — external-service hardening: replace the Tavily quota check-then-act with an atomic `find_one_and_update`).**

Phase 1 + Phase 2 + Phase 3 + Phase 4 + Phase 5 are fully SHIPPED. Phase 5 (#14–#18 / TD28–TD32, frontend correctness + quick wins) shipped Chat 5.13, 2026-06-08, across BOTH repos — one frontend code commit (TD28, frontend HEAD `f59958`) + three backend code commits (TD29 dead-import, TD31 ISIN pattern, TD32 regex `$options`; deployed code HEAD `090d96c`); TD30 was a doc-drift confirmation (no code). Per the standing rule, Phase 6 (#19–#24, external-service hardening) begins in a fresh chat to keep context clean.

Items completed since this file was created:
- #1 (TD14) — SHIPPED 2026-06-02 (Chat 5.9)
- #2 (TD10) — SHIPPED 2026-06-02 (Chat 5.9)
- #3 (TD15) — SHIPPED 2026-06-02 (Chat 5.9)
- #4 (TD16) — SHIPPED 2026-06-06 (Chat 5.10)
- #6 (TD18) — SHIPPED 2026-06-06 (Chat 5.10)
- #5 (TD17) — SHIPPED 2026-06-06 (Chat 5.10)
- #7 (TD19) — SHIPPED 2026-06-06 (Chat 5.10)
- #8 (TD20) — SHIPPED 2026-06-06 (Chat 5.10)
- #9 (TD23) — SHIPPED 2026-06-08 (Chat 5.11)
- #10 (TD24) — SHIPPED 2026-06-08 (Chat 5.11)
- #11 (TD25) — SHIPPED 2026-06-08 (Chat 5.11)
- #12 (TD26) — SHIPPED 2026-06-08 (Chat 5.12)
- #13 (TD27) — SHIPPED 2026-06-08 (Chat 5.12)
- #14 (TD28) — SHIPPED 2026-06-08 (Chat 5.13)
- #15 (TD29) — SHIPPED 2026-06-08 (Chat 5.13)
- #16 (TD30) — SHIPPED 2026-06-08 (Chat 5.13)
- #17 (TD31) — SHIPPED 2026-06-08 (Chat 5.13)
- #18 (TD32) — SHIPPED 2026-06-08 (Chat 5.13)

When you finish an item, change its row's Status column from `OPEN` to `SHIPPED <YYYY-MM-DD> (Chat <N>)` and advance the "Next item to start" pointer. Do not delete shipped rows — they are the audit trail.

---

## Ordering rationale

Ordered to minimize rework. Principle: **fix the code surface before adding features on top of it.**

1. **Phase 1** — Unblock ops first (no code; immediate value; restores weekly digest).
2. **Phase 1** — Reconcile documentation (TD15) before any chat that reads files with F-comments; otherwise future chats hallucinate against unmapped F-numbers.
3. **Phase 2** — Fix transactions/holdings/audit invariants BEFORE Chat 9 touches `holdings` (stop_loss + realized P&L hide). SHIPPED Chat 5.10.
4. **Phase 3** — Fix intraday correctness early; every dashboard load and every sell-side suggestion depends on it. SHIPPED Chat 5.11.
5. **Phase 4** — Storage hygiene (TTL + body purge) BEFORE Chat 10 GO LIVE — real ICICI data import is when collections start filling for keeps. SHIPPED Chat 5.12.
6. **Phases 5-7** — Frontend correctness + external-service hardening + reconciliation alerting; mostly independent of one another, can be batched. Phase 5 SHIPPED Chat 5.13.
7. **Phase 8** — New features (Chats 6-8) AFTER underlying services are correct; Chat 8 (watchlist) must come after Phase 4 (storage) + Phase 6 (Tavily race) since it multiplies data volume.
8. **Phase 9** — Cross-cutting cleanup (`datetime.utcnow()` sweep, Python ceiling, pytest harness, ops gaps) right before GO LIVE so launch lands on one clean state.
9. **Phase 10** — Chat 9 pre-launch cleanup (F11 + realized P&L hide + stop_loss wiring).
10. **Phase 11** — Chat 10 GO LIVE (F7 real data import) — last, so test pollution gets wiped in one operation.
11. **Phase 12** — Deferred TDs (TD1, TD3, TD7) — after launch is stable.
12. **New items (Chat 5.9)** — TD21 (registry-generated crontab migration) + TD22 (track_suggestion_outcomes daily failure), filed mid-stream; see the NEW ITEMS phase below.

---

## Item legend

- **Source column codes:**
 - `TD<N>` — Tech debt registry row in `Project_State.md` Section 18
 - `P0/P1/P2/P3-<N>` — Code review finding (see `code_review_findings_chat_6_audit.md` if archived, or the Chat 5.8 review)
 - `Chat <N>` — Pre-existing chat in the Section 13 chat split plan
 - `F<N>` — Feature ticket (mirrored from external registry; see TD15)
 - `Ops gap` — Operational gap called out in the review's ops-gaps section
- **Status column codes:**
 - `OPEN` — Not started
 - `IN PROGRESS (Chat <N>)` — Being worked in the named chat
 - `SHIPPED <YYYY-MM-DD> (Chat <N>)` — Done; commit landed
 - `DEFERRED` — Acknowledged and intentionally pushed to a later phase
 - `DROPPED` — Explicitly de-scoped; note rationale in the row

---

## PHASE 1 — Unblock operations (no code; do this week) — SHIPPED Chat 5.9

| # | Source | Item | Files / surface | Status |
|---|---|---|---|---|
| 1 | TD14 / P1-5 | Fix Sunday 07:00 IST crontab line: drop bogus `--notify --run-type scheduled` flags. Optional: run `scripts/run_weekly_suggestions.py --direction=both` manually for immediate digest recovery. Also confirm whether nightly `cron_health_check` ntfy + email alerts have actually been arriving — if not, second silent failure in dual-transport path. **Chat 5.9 closed build-right: Part A flags removed from crontab (verified via `crontab -l`); Part B `CRON_REGISTRY` entry renamed `run_weekly_suggestions` → `weekly_suggestions` (commit `c097b473`) to match the heartbeat the script writes, killing the phantom Sunday MISSING. Dual-transport confirmed HEALTHY by inspection (email + ntfy both arrive daily). The daily 21:00 health alert is a SEPARATE failure → filed as #47 (TD22).** | EC2 `crontab -e` + `app/services/cron_heartbeat_service.py` | SHIPPED 2026-06-02 (Chat 5.9) |
| 2 | TD10 | Remove redundant `0 0 * * 0 find ... -size +10M ...` crontab line (logrotate replaces it). Verify first logrotate cycle completed (next: 2026-05-31 Sun 00:00 IST window) then remove. **Chat 5.9: GATE PASSED (rotation trail `cron-*.log.1` 2026-05-31 + `.2.gz` 2026-05-24 present for all 10 logs) AND the `find -size +10M` line was found ABSENT from the live crontab — already removed in a prior session or never deployed. End state satisfied; no edit needed.** | EC2 `crontab -e` | SHIPPED 2026-06-02 (Chat 5.9) |
| 3 | TD15 | Reconcile F-number fix registry: read every file at HEAD that carries an F-comment (F2/F3/F4/F5/F7/F8/F12/F14/F16-F21/F23/F27-F29/F79/F80/F82), map each F-number to its file + one-line description, add rows to `Project_State.md` Section 18. Do BEFORE any code chat. Also: this may surface that items #26 (P2-6) and #43 (TD1) are already partially addressed by an F-ticket. **Chat 5.9: grepped at HEAD `c097b473` — 25 unique in-code F-numbers (the "~20" estimate was low; fix-registry subset is 21) across TWO colliding namespaces (feature-F vs fix-Chat-5.5+-F). Authored the "F-number fix registry" subsection in Section 18 with a Kind column. Recovered the truncated Section 18 (and Sections 16-tail through 22) that the Chat 5.8 doc commit `8f74b50` had silently amputated. No overlap found that lets #26 or #43 drop — both stay OPEN/DEFERRED.** | `docs/Project_State.md` | SHIPPED 2026-06-02 (Chat 5.9) |

## PHASE 2 — Transactions / holdings / audit consistency — SHIPPED Chat 5.10

Fix this surface before Chat 9 touches it. All five items shipped + verified on EC2 against localhost:8000.

| # | Source | Item | Files | Status |
|---|---|---|---|---|
| 4 | P1-1 | Make `PATCH /transactions/{id}` and `DELETE /transactions/{id}` write `transactions_audit` BEFORE applying the change. Mirror the suggestions feedback handler pattern. **Chat 5.10 SHIPPED: both handlers now `log_change(...)` BEFORE `update_one(...)`; PATCH audits a computed `{**before, **update_fields}` after-state then applies then re-reads for the response; `validate_replay` still runs first so a rejected edit/delete writes no audit row.** | `app/routers/transactions.py` `edit_transaction` + `delete_transaction` | SHIPPED 2026-06-06 (Chat 5.10) — commit `17f9f94` |
| 5 | P1-3 | Add `validate_replay` to `/portfolio/holdings/{isin}/sell` and to the manual import path so backdated SELLs that produce negative quantity get 400'd, not silently logged. **Chat 5.10 SHIPPED: `/sell` replays `existing_txns + [proposed_sell]` and 400s before the ledger write; `add_manual_transactions.py` gates SELL inserts on `validate_replay` and aborts with `RuntimeError` instead of silently staging. Existing point-in-time `held_qty` check kept for the clearer common-case message.** | `app/routers/holdings.py` `sell`; `scripts/add_manual_transactions.py` insert loop | SHIPPED 2026-06-06 (Chat 5.10) — commit `5cf3087` |
| 6 | P1-2 | Delete duplicate route handler `list_transactions` (lines ~329-335); keep `get_holding_transactions` (~163-180). **Chat 5.10 SHIPPED: deleted the shadowed EOF `list_transactions` handler; `get_holding_transactions` is the sole handler for `GET /portfolio/holdings/{isin}/transactions`. Behaviour-neutral (first-registered handler already won every request).** | `app/routers/holdings.py` | SHIPPED 2026-06-06 (Chat 5.10) — committed after `17f9f94`, before `5cf3087` |
| 7 | P2-9 | Make `add_buy` / `sell` non-atomic path safer: wrap `recompute_holding` in try/except, return success with a warning flag if recompute fails. Or use Mongo M10 transactions for atomicity. **Chat 5.10 SHIPPED (warning-flag path, user-confirmed): both handlers wrap `recompute_holding` in try/except; on exception they `log.exception(...)` and return 2xx `{status:"recorded_with_warning", isin, warning}` so the persisted ledger write isn't masked. `recompute_holding` returning None stays a legitimate full-exit success outside the except. M10 multi-doc transactions explicitly REJECTED — per-step session latency on a single-user box not worth it.** | `app/routers/holdings.py` `add_buy` + `sell` (+ module logger) | SHIPPED 2026-06-06 (Chat 5.10) — commit `fb23307` |
| 8 | P2-10 | Serialize `recompute_holding` per-ISIN: per-ISIN advisory lock doc with TTL, OR API-layer mutex keyed by ISIN. **Chat 5.10 SHIPPED (advisory-lock doc, user-confirmed): `recompute_holding` wraps its body (renamed `_recompute_holding_impl`) in `_per_isin_recompute_lock`, a CM that inserts a doc keyed `_id==isin` into the new `recompute_locks` collection (atomic via unique `_id` index), releases in `finally`, and is TTL-reclaimed after 60s. `asyncio.Lock` REJECTED — confirmed at HEAD that every holdings handler is sync `def` under sync Uvicorn, so asyncio.Lock wouldn't apply; `threading.Lock` rejected because it's blind to the out-of-process scripts. Lock lives at the service layer so all callers (API + scripts) are covered.** | `app/services/holdings_service.py`; `app/db/client.py`; `app/db/indexes.py` | SHIPPED 2026-06-06 (Chat 5.10) — commit `b34721e` |

## PHASE 3 — Intraday & price correctness — SHIPPED Chat 5.11

All three items shipped in ONE backend code commit (`a2806cd`) + verified on EC2 against localhost:8000. All three touch only `app/services/price_service.py`.

| # | Source | Item | Files | Status |
|---|---|---|---|---|
| 9 | P1-4 / TD23 | Guard `_intraday_row_from_df` against yfinance returning yesterday's bar on market holidays: if bar timestamp's IST date != today, return None. **Chat 5.11 SHIPPED: the function now reads the latest 5m bar's index timestamp (`clean.index[-1]`) and returns None when its IST date != today's IST date — yfinance `period="1d"` returns the prior trading day's bars on an NSE holiday. Added module-level `IST = timezone(UTC+5:30)` (India has no DST) + `_to_ist()` helper (tz-aware → `astimezone`; tz-naive → treated as UTC first, matching the existing `_df_to_rows` / `annotate_with_current_price` naive→UTC convention). "today" is derived from the passed-in `captured_at`. Verified on EC2: a today-dated synthetic bar returns a dict; a yesterday-dated bar returns None.** | `app/services/price_service.py` `_intraday_row_from_df` (+ new `IST`/`_to_ist` helpers) | SHIPPED 2026-06-08 (Chat 5.11) — commit `a2806cd` |
| 10 | P2-14 / TD24 | Align `price_stale` docstring vs code: doc says "4 trading days", code says `timedelta(days=6)`. Pick one; pragmatic fix is update docstring. **Chat 5.11 SHIPPED (CODE is canonical — user-delegated decision): kept `timedelta(days=6)`; updated the docstring "more than 4 trading days old" → "more than 6 calendar days old" and added an inline comment noting 6 calendar days ≈ 4 NSE trading days across a weekend (the clear original intent). Doc-/comment-only; zero behaviour change. Verified: `/portfolio/holdings` still returns `price_stale` correctly (false on a fresh price).** | `app/services/price_service.py` `price_stale` docstring + inline comment | SHIPPED 2026-06-08 (Chat 5.11) — commit `a2806cd` |
| 11 | P2-13 / TD25 | Rewrite `bulk_get_previous_closes` to push the filter into the Mongo pipeline (or loop `find_one` per ISIN). Currently pulls ~34k price docs per dashboard request. **Chat 5.11 SHIPPED (per-ISIN `find_one` — user-delegated decision): rewrote the body to delegate to the existing single-ISIN `get_previous_close` (an indexed `find_one({"date": {"$lt": latest}}, sort=[("date",-1)])` point-query per ISIN) instead of `$push`-ing every `{date, close}` for every ISIN into an in-memory `all_dates` array and filtering in Python. Eliminates the ~34k-doc pull per dashboard request; keeps the Decimal128/Decimal normalization in exactly one place. Chosen over an aggregation-pipeline rewrite because it evolves existing code (no new query pattern) and the `(isin, date)` index makes each call a single-doc point-query. Verified on EC2: `bulk_get_previous_closes` result is byte-identical to per-ISIN `get_previous_close` for all held ISINs.** | `app/services/price_service.py` `bulk_get_previous_closes` | SHIPPED 2026-06-08 (Chat 5.11) — commit `a2806cd` |

## PHASE 4 — Storage hygiene (must land BEFORE Chat 10 GO LIVE) — SHIPPED Chat 5.12

| # | Source | Item | Files | Status |
|---|---|---|---|---|
| 12 | P2-3 | Add TTL index on `prices_intraday.captured_at` with `expireAfterSeconds = 90 * 86400`. **Chat 5.12 SHIPPED (TD26): confirmed at HEAD that `_intraday_row_from_df` writes `captured_at` as a BSON Date (`datetime.now(timezone.utc)`, serialized to UTC Date) so the TTL actually expires docs — a TTL silently no-ops on a string/Decimal field. Added `captured_at_ttl` (ASC, `expireAfterSeconds = 90*86400 = 7776000`) alongside the existing non-TTL `captured_at_desc` (ASC vs DESC are different key patterns, so both coexist — mirrors `cron_heartbeats` `started_at_ttl` + `started_at_desc`). `ensure_all_indexes` stays purely additive (no drop). Verified on EC2: `db.prices_intraday.getIndexes()` shows `captured_at_ttl` on `{captured_at:1}` with `expireAfterSeconds:7776000`; all four indexes intact.** | `app/db/indexes.py` | SHIPPED 2026-06-08 (Chat 5.12) |
| 13 | P2-4 | New `scripts/purge_news_bodies.py` daily cron: `$unset {body_text: ""}` on classified `news_articles` whose `fetched_at` is older than 30 days; stamp `body_purged_at`. Register in `CRON_REGISTRY`. **Chat 5.12 SHIPPED (TD27): field corrections vs the original spec — the bulky field is `body_text` (NOT `body`), and age keys on `fetched_at` (always present via `default_factory=utcnow`; `published_at` is nullable so it would strand undated docs). Script mirrors `refresh_prices_intraday.py` (`cron_run("purge_news_bodies")` heartbeat, `hb.metadata[...]`, `hb.mark_skipped("no_expired_bodies")` on nothing-to-do); adds `--dry-run` (count-only). Filter `{classified:True, fetched_at:{$lt:cutoff}, body_purged_at:None, body_text:{$nin:["",None]}}`; write `{$unset:{body_text:""}, $set:{body_purged_at: now}}` (idempotent). `CronSpec.cron_name == cron_run() name == "purge_news_bodies"` (TD14 contract). Crontab line at 02:30 IST (`30 2 * * *`) with `>> cron-news-purge.log 2>&1`. Verified on EC2 against the real `portfolio` DB: dry-run reported 1 candidate, live run purged 1, sentinel returned `body_text` absent + `body_purged_at` a Date, success heartbeat `metadata.purged:1`; `/cron/heartbeats` shows it `healthy:true, expected_today:true`.** | `scripts/purge_news_bodies.py` (NEW) + crontab + `CRON_REGISTRY` | SHIPPED 2026-06-08 (Chat 5.12) |

## PHASE 5 — Frontend correctness & quick wins — SHIPPED Chat 5.13

Spans BOTH repos: #14 is frontend (one commit, frontend HEAD `f59958`); #15/#17/#18 are backend (three commits, deployed code HEAD `090d96c`); #16 is a doc-drift confirmation (no code). All verified on EC2 — frontend via `~/deploy-ui.sh` + `npm run build`; backend via `ssh ubuntu@100.112.20.41` + `curl localhost:8000` with positive landed-assertions per item.

| # | Source | Item | Files | Status |
|---|---|---|---|---|
| 14 | P2-2 | Swap `invalidateQueries` → `refetchQueries` in `notes-panel.tsx` (lines 43, 46) and `refresh-button.tsx` (lines 17-19). **Chat 5.13 SHIPPED (TD28): minimal name-swap (no `async`/`await` reorder). At HEAD the two `notes-panel.tsx` calls were at lines 42 + 45 (`["holding", holding.isin]`, `["dashboard"]`); the three `refresh-button.tsx` calls were at lines 17-19 inside the existing `await Promise.all([...])` (`["dashboard"]`, `["reconciliation"]`, `["cost-basis"]`). Aligns these two outliers with the project-wide synchronous-refetch convention (Project_State Section 14). Verified on frontend HEAD `f59958`: `grep invalidateQueries` → 0; `refetchQueries` counts notes-panel:2 + refresh-button:3 = 5; `~/deploy-ui.sh` build clean.** | `components/notes-panel.tsx`, `components/refresh-button.tsx` | SHIPPED 2026-06-08 (Chat 5.13) — frontend HEAD `f59958` |
| 15 | P3-3 | Remove unused `from pydoc import doc` import. **Chat 5.13 SHIPPED (TD29): dead import at line 6, immediately shadowed by local `doc` variables in the serializer helpers. Behaviour-neutral. Verified on backend HEAD `090d96c`: `grep "from pydoc import doc"` → empty (literal string, true negative).** | `app/routers/holdings.py` line 6 | SHIPPED 2026-06-08 (Chat 5.13) — backend HEAD `090d96c` |
| 16 | P3-6 | Fix doc drift: `Project_State.md` Section 10 says `MONGODB_URL`, code uses `MONGODB_URI`. **Chat 5.13 SHIPPED (TD30): confirmed at HEAD that Project_State Section 10 already reads `MONGODB_URI` (with the explicit master_todo #16 note that earlier versions said `MONGODB_URL`) — the correction had landed in the Chat 5.12 Project_State. Row closed with no further code/doc edit beyond stamping it SHIPPED here. Doc-only confirmation; zero behaviour change.** | `docs/Project_State.md` | SHIPPED 2026-06-08 (Chat 5.13) |
| 17 | P3-7 | Add `pattern=r"^[A-Z0-9]{12}$"` to ISIN Path params on `/suggestions/{isin}/audit` and `/suggestions/{isin}/feedback`. **Chat 5.13 SHIPPED (TD31): added `pattern=r"^[A-Z0-9]{12}$"` alongside the existing `min_length=12, max_length=12` on the two ISIN `Path(...)` params — `get_feedback_audit_for_isin` (line 240, GET `/suggestions/{isin}/audit`) and `submit_feedback` (line 260, POST `/suggestions/{isin}/feedback`). `/runs/{run_id}` left untouched (it's an ObjectId, not an ISIN). Malformed ISINs now 422 at the boundary instead of reaching Mongo. Verified on backend HEAD `090d96c`: `grep -F 'pattern=r"^[A-Z0-9]{12}$"'` → 2 matches; a 12-char lowercase ISIN `INE002a01018` → 422 (rejected by pattern, not length); valid `INE002A01018` → 200.** | `app/routers/suggestions.py` ~245 | SHIPPED 2026-06-08 (Chat 5.13) — backend HEAD `090d96c` |
| 18 | P3-8 | Drop `"$options": "i"` from `transactions/search` regex — symbols already uppercased pre-query; "i" disables the index. **Chat 5.13 SHIPPED (TD32): the regex was at lines 91-92 in `search_transactions` (not ~102-115; that range is the date-bound block). Input is already `symbol.upper()` and symbols are stored uppercase, so the `"i"` flag was pure redundancy that disabled the `(symbol, trade_date)` index on the prefix regex. Dropped the flag (`query["symbol"] = {"$regex": f"^{escaped}"}`) and corrected the now-false "(case-insensitive)" inline comment. Behaviour-neutral for callers; restores index use. Verified on backend HEAD `090d96c`: `grep '$options'` → empty; clean regex present at line 113; `GET /transactions/search?symbol=tr` returns `total: 20` (parity with pre-change).** | `app/routers/transactions.py` ~102-115 | SHIPPED 2026-06-08 (Chat 5.13) — backend HEAD `090d96c` |

## PHASE 6 — External-service hardening

| # | Source | Item | Files | Status |
|---|---|---|---|---|
| 19 | P2-5 | Replace Tavily quota check-then-act with atomic `find_one_and_update` against `tavily_quota`. | `app/services/tavily_client.py` ~110-145 | OPEN |
| 20 | P3-4 | Add 1-2 attempt retry with 30-60s backoff inside `notify.email()` on transient 5xx / 429. Don't retry 400s. | `app/services/notify.py` | OPEN |
| 21 | P3-5 | Persist suggestion run BEFORE digest formatting; pass `inserted_id` explicitly to `send_combined_digest`. | `app/services/digest_delivery.py` ~470-490 | OPEN |
| 22 | P3-1 | Reject NaN in `_to_decimal`: `if isinstance(v, float) and v != v: raise ValueError("NaN not allowed")`. | `app/models/_common.py` ~12 | OPEN |
| 23 | P2-12 | Add fallback log file for `cron_run` heartbeat-insert failure (`/home/ubuntu/cron-heartbeat-fallback.log`); `cron_health_check` reads both sources. | `app/services/cron_heartbeat_service.py` + `scripts/cron_health_check.py` | OPEN |
| 24 | P3-9 | Wrap `cron_health_check.main` Mongo reads in try/except that fires an "anomaly: health-check itself failed" ntfy on errors channel even when Mongo is unreachable. | `scripts/cron_health_check.py` | OPEN |

## PHASE 7 — Reconciliation alerting & feedback correctness

| # | Source | Item | Files | Status |
|---|---|---|---|---|
| 25 | P2-7 | Make `take_auto_snapshot` fire `push_public("price", ...)` when drift change exceeds threshold against last manual snapshot. ntfy only (email too noisy on daily cron). | `app/services/reconciliation.py` ~78-115 | OPEN |
| 26 | P2-6 / TD1 | Decide & implement: direction-aware feedback relabel. Add `"direction": payload.direction` to outcome filter in `submit_feedback`. Folds in TD1's lingering question; may overlap with an F-ticket — confirm via #3 (TD15) before patching. **Chat 5.9 note: TD15 reconciliation found no F-ticket already covering this; stays OPEN.** | `app/routers/suggestions.py` ~310-325 | OPEN |

## PHASE 8 — New features per chat split plan

Do AFTER Phases 2 + 6 so underlying surfaces are correct. Chats 6 and 7 are independent; Chat 8 (watchlist) must come last among these.

| # | Source | Item | Files / surface | Status |
|---|---|---|---|---|
| 27 | Chat 6 / F1 + F3 | Ad-hoc chat about suggestions (F1) + ad-hoc chat about a specific holding (F3). Share `conversations` collection scaffolding. New `POST /chat/suggestions` and `POST /chat/holdings/{isin}` endpoints. Frontend chat surface. | `routers/conversations.py` (NEW), `services/conversation_service.py` (NEW), frontend chat components | OPEN |
| 28 | Chat 7 / F12 + F15 | `/portfolio/risk-summary` (concentration & risk alerts) + `/portfolio/by-tag?tag=X` (tag-based portfolio views). | `routers/portfolio.py`, `services/portfolio_service.py`, frontend dashboard additions | OPEN |
| 29 | Chat 8 / F13 | Watchlist: `build_universe` becomes NIFTY 100 ∪ watchlist ∪ held − excluded. Extend `refresh_fundamentals.py` AND `fetch_news_for_universe.py` to cover watchlist ISINs. New `/watchlist` CRUD endpoints (reuse `monitored_stocks` with `status="watchlist"`). Frontend watchlist surface. | `services/suggestion_engine.py`, `scripts/refresh_fundamentals.py`, `scripts/fetch_news_for_universe.py`, `routers/suggestions.py`, frontend new page | OPEN |

## PHASE 9 — Cross-cutting cleanup before GO LIVE

| # | Source | Item | Files | Status |
|---|---|---|---|---|
| 30 | P2-1 | Replace 9 `datetime.utcnow()` call sites with project's `utcnow()` from `app.models._common`. | `routers/portfolio.py:43`, `services/scoring_service.py:116,813,890`, `services/dossier_service.py:166,192`, `services/fundamentals_service.py:370,485,505` | OPEN |
| 31 | P2-8 | Audit every `datetime.now(timezone.utc)` (tz-aware) Mongo write site; replace with `utcnow()`. Add CI lint rule (ruff custom or grep). | `routers/transactions.py:196,245,267`, `services/reconciliation.py:78,~138`, `services/tavily_client.py:50,~55`, `services/price_service.py:155` | OPEN |
| 32 | P3-2 | Pin `requires-python = ">=3.12,<3.14"` in `pyproject.toml`. | `pyproject.toml` | OPEN |
| 33 | Review note | Stand up basic pytest harness. Minimum coverage: `_fifo_replay`, `preview_sell`, `validate_replay`, `recompute_holding` idempotency, `submit_feedback` write-before-apply ordering, `take_auto_snapshot` drift math. | `tests/*` (NEW) | OPEN |
| 34 | Ops gap | Audit `/health` endpoint — does it actually ping Mongo or just return 200? Add Mongo + optionally yfinance heartbeat. | `app/main.py` | OPEN |
| 35 | Ops gap | Add ntfy push on `insert_intraday_quotes` exception during market hours. | `scripts/refresh_prices_intraday.py` | OPEN |
| 36 | Ops gap | Add `POST /admin/recompute/{isin}` (Tailscale-only). Replaces SSH-shell recovery for stuck holdings (#7 fallback). | `app/routers/admin.py` (NEW) | OPEN |
| 37 | Ops gap | Rehearse Atlas backup → fresh-DB restore for `monitored_stocks` + `suggestion_outcomes` + `digest_deliveries`. Document exact `mongorestore` command in `Project_State.md`. | `docs/Project_State.md` | OPEN |
| 38 | Ops gap | Switch backend logging to JSON-structured (basicConfig → custom formatter or `python-json-logger`). | `app/main.py` (logging config) | OPEN |

## PHASE 10 — Chat 9 pre-launch cleanup

| # | Source | Item | Files | Status |
|---|---|---|---|---|
| 39 | Chat 9 / F11 | Capital gains pack. New `GET /tax/capital-gains?fy=YYYY-YY` returning STCG/LTCG breakdown per lot for the financial year. Frontend tax view page. | `routers/tax.py` (NEW), `services/tax_service.py` (NEW), frontend tax page | OPEN |
| 40 | Chat 9 | Realized P&L UI hide. Backend field stays (FIFO needs it); frontend stops rendering everywhere it currently shows. | Frontend: holdings-table, holding-stats, totals-row, holding-header | OPEN |
| 41 | Chat 9 / TD6 | Wire `holdings.stop_loss`. Reader + writer + alerts: when intraday price crosses below stop_loss, fire ntfy. Frontend stop_loss edit field on holding drill-down. Closes TD6. | `routers/holdings.py` (PATCH expansion), `services/price_service.py` (alert trigger), `scripts/refresh_prices_intraday.py`, frontend `holding-stats.tsx` | OPEN |

## PHASE 11 — GO LIVE

| # | Source | Item | Files | Status |
|---|---|---|---|---|
| 42 | Chat 10 / F7 | One-time real ICICI data import. Wipe + re-import via `scripts/refresh_from_icici.py` wrapper. Default wipe-and-replace scope: ONLY `transactions`, `transactions_staging`, `holdings`. Preserve `monitored_stocks`, `suggestion_outcomes`, `digest_deliveries`, all `instruments_*`, `prices_*`, `news_articles`. | `scripts/refresh_from_icici.py` (NEW or wrapping existing import_orderbooks) | OPEN |

## PHASE 12 — Post-launch deferred work

| # | Source | Item | Files | Status |
|---|---|---|---|---|
| 43 | TD1 | Make `monitored_stocks` direction-aware: add `direction` field, dual rows per ISIN. Reconcile with #26 — if that already solved the practical pain, this becomes optional internal cleanup. | `models/monitored_stock.py`, `routers/suggestions.py`, `services/suggestion_engine.get_excluded_isins` | DEFERRED |
| 44 | TD3 | Split `dossier_service.valuation_verdict` from single string into `{verdict, rationale}` for cleaner UI. | `services/dossier_service.py`, frontend `suggestion-card.tsx` | DEFERRED |
| 45 | TD7 | Refactor `CandidateScore` so sell-side groups live as first-class fields instead of flowing through `group_meta`. Removes the buy/sell asymmetry in the data model. | `models/suggestion.py`, `services/scoring_service.py`, `services/explainability.py`, frontend | DEFERRED |

## NEW ITEMS — filed Chat 5.9 (do not renumber existing rows)

| # | Source | Item | Files / surface | Status |
|---|---|---|---|---|
| 46 | TD21 | Registry-generated crontab migration (the deferred scheduler-architecture work). `CRON_REGISTRY` gains a parseable cron expression per `CronSpec` → new `scripts/render_crontab.py` renders a committed `ops/crontab` → `deploy.sh` installs it + a drift-validation step (`crontab -l` diff vs rendered). Version-controls the schedule and makes TD14-class drift structurally impossible, while keeping process isolation + deploy-safety (explicitly chosen OVER in-process APScheduler, which on the 1 GB t3.micro would let the ~5-min Sunday dossier run compete with the live API and die on every `systemctl restart`). Update the F4 "no silent failures" triad in Project_State §9 when it lands. Its own dedicated chat. | `app/services/cron_heartbeat_service.py`, `scripts/render_crontab.py` (NEW), `ops/crontab` (NEW), `deploy.sh` | OPEN |
| 47 | TD22 | `track_suggestion_outcomes` cron FAILS every weekday (19:45 IST; the 21:00 IST health email shows `track_suggestion_outcomes: 0 success / 1 failure` daily). Distinct from TD14 — surfaced during the Chat 5.9 TD14 investigation. Root-cause the daily failure (read `cron-outcomes.log` at HEAD + the script body) and fix. | `scripts/track_suggestion_outcomes.py`, `app/services/outcome_tracker.py` | OPEN |

---

## Summary by phase

| Phase | Items | Theme | Gating |
|---|---|---|---|
| 1 | 1-3 | Unblock ops + reconcile docs | No code — SHIPPED Chat 5.9 |
| 2 | 4-8 | Transactions/holdings/audit invariants | Foundation for Chat 9 + 10 — SHIPPED Chat 5.10 |
| 3 | 9-11 | Intraday & price correctness | Foundation for Chat 8 sell-side — SHIPPED Chat 5.11 |
| 4 | 12-13 | Storage hygiene (TTL + purge) | Foundation for Chat 10 real data — SHIPPED Chat 5.12 |
| 5 | 14-18 | Frontend correctness + quick wins | Independent — SHIPPED Chat 5.13 |
| 6 | 19-24 | External-service hardening | Foundation for Chat 8 (parallelism) — next |
| 7 | 25-26 | Reconciliation alerting + feedback direction | Standalone |
| 8 | 27-29 | New features (Chats 6, 7, 8) | Underlying surfaces correct |
| 9 | 30-38 | Pre-launch sweep + ops gaps | Last clean state before GO LIVE |
| 10 | 39-41 | Chat 9 pre-launch cleanup | TD6 + F11 + realized P&L hide |
| 11 | 42 | Chat 10 GO LIVE (F7 real data import) | Everything else done |
| 12 | 43-45 | Deferred TDs (TD1, TD3, TD7) | After launch stable |
| NEW | 46-47 | TD21 scheduler migration + TD22 outcomes-cron failure | Filed Chat 5.9; schedule independently |

---

## Cross-references

- `docs/Project_State.md` Section 0 — bootstrap (this file is item 5 on the read list)
- `docs/Project_State.md` Section 13 — historical "shipped" log and chat split plan
- `docs/Project_State.md` Section 18 — TD registry (each row cross-references its master_todo `#N`)
- `docs/data_flow.md` — data flow reference

## How to update this file

- **Every chat ends with two doc commits:** `Project_State.md` full-file replacement AND a `master_todo.md` update (status changes + current-position pointer advance).
- **Never delete shipped rows.** Change `OPEN` → `SHIPPED <YYYY-MM-DD> (Chat <N>)`. Shipped rows are the audit trail.
- **Adding new items mid-stream** (e.g., a fresh bug discovered): append the row at the END of the appropriate phase (or in the NEW ITEMS phase); do not renumber existing items (item numbers are stable references).
- **Re-ordering between phases:** allowed if the rationale block explains why; document the reason in the row's Notes column if needed.
- **If a row becomes obsolete** (e.g., TD15 reconciliation reveals an F-ticket already shipped a fix): change Status to `DROPPED <YYYY-MM-DD> (Chat <N>) — <one-line reason>`. Do not delete.
- **Current-position pointer** at the top must advance every time the lowest-numbered OPEN row changes.

End of master_todo.md.
