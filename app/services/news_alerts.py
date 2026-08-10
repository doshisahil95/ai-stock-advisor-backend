"""News alert evaluator (master_todo #57).

A damaging or highly favourable news item on a name the user cares about
(active holdings with "news" in alert_on, plus watchlisted/flagged names)
should push an alert so buy/sell decisions can react.

This is the news-fetch-path analog of the #41 stop-loss / #56 target-price
intraday evaluators: same shape (find eligible subjects, success-gated dedup,
ntfy-only via push_public, persist an Alert to alerts_log as the durable audit
row), but the trigger is a discrete news EVENT rather than a rising price edge.

Called by scripts/fetch_news_for_universe.py right AFTER classify_unclassified
(so only classified, entity-correct articles are evaluated) -- no parallel
fetch/classify here; the cron stays a thin caller.

Depends on #50 (entity mis-tagging fix): the eligible-ISIN query below is only
as trustworthy as news_articles.entities_isins. #50 tightened entities_isins so
an alert never fires on wrong-company news.

Behaviour:
  - Eligible ISINs = active holdings with "news" in alert_on  UNION  all
    watchlisted ISINs (get_watchlist_isins). Watchlist names were explicitly
    flagged, so they are always news-alert-eligible.
  - An article qualifies if it is classified, severity == "high", carries a
    non-noise theme, and was fetched within the recency window.
  - A news item is a discrete event: it fires AT MOST ONCE per (isin, article).
    Dedup is success-gated -- only a previously DELIVERED news_event alert
    (delivery_status == "sent") whose cited_news_ids contains this article
    suppresses a re-fire. A prior send that FAILED does not suppress, so a
    transient ntfy outage can't silently swallow a real story -- the next run
    retries.
  - Transport is ntfy-only via push_public("news", ...); every attempt is
    persisted to alerts_log (Alert alert_type="news_event") whether the push
    succeeded or not.

Returns the number of alerts fired (attempted) this run.
"""

from __future__ import annotations

import logging
from datetime import timedelta

from pymongo import DESCENDING

from app.db.client import Collections
from app.models._common import utcnow
from app.models.alert_log import Alert, TriggerData
from app.services.notify import push_public
from app.services.suggestion_engine import get_watchlist_isins

log = logging.getLogger(__name__)

# A theme set that is exactly {"noise"} (or empty) contributes nothing to a
# buy/sell decision -- do not alert on it even at high severity.
_NOISE_ONLY = frozenset({"noise"})


def _eligible_isin_meta() -> dict[str, dict]:
    """isin -> {symbol, name} for every news-alert-eligible name.

    Held names must have "news" in alert_on; watchlisted names are always
    eligible. Symbol/name are resolved from the holding doc where available,
    else from instruments (for watchlist-only names outside the portfolio).
    """
    meta: dict[str, dict] = {}

    # Held with "news" in alert_on.
    for h in Collections.holdings().find(
        {"deleted_at": None, "alert_on": "news"},  # array-membership match
        {"_id": 0, "isin": 1, "symbol": 1, "name": 1},
    ):
        isin = h.get("isin")
        if isin:
            meta[isin] = {
                "symbol": h.get("symbol") or isin,
                "name": h.get("name") or "",
            }

    # Watchlisted names (status=="watchlist"). Always eligible.
    watch = get_watchlist_isins()
    missing = [i for i in watch if i not in meta]
    if missing:
        for inst in Collections.instruments().find(
            {"isin": {"$in": missing}},
            {"_id": 0, "isin": 1, "symbol": 1, "name": 1},
        ):
            isin = inst.get("isin")
            if isin:
                meta[isin] = {
                    "symbol": (inst.get("symbol") or isin),
                    "name": inst.get("name") or "",
                }
        # Watchlist ISINs not resolvable in instruments still get a stub so the
        # article -> isin match can fire (symbol falls back to the ISIN).
        for isin in missing:
            meta.setdefault(isin, {"symbol": isin, "name": ""})

    return meta


def _already_fired(alerts_log, isin: str, article_id) -> bool:
    """True if a DELIVERED news_event for this (isin, article) already exists.

    Reuses the alerts_log isin_type_sent_desc index prefix (isin, alert_type,
    sent_at); the cited_news_ids membership is an added equality on the
    multikey list field.
    """
    return (
        alerts_log.find_one(
            {
                "isin": isin,
                "alert_type": "news_event",
                "delivery_status": "sent",
                "cited_news_ids": article_id,  # membership on the list field
            },
            sort=[("sent_at", DESCENDING)],
        )
        is not None
    )


def evaluate_news_alerts(window_days: int = 3) -> int:
    """Fire news_event alerts for eligible names on high-severity fresh news.

    window_days: only consider articles fetched within this many days (the
    daily cron means fresh stories land continuously; 3 days tolerates a
    missed run without re-alerting ancient news, since dedup is per-article).
    """
    meta = _eligible_isin_meta()
    if not meta:
        return 0

    eligible_isins = list(meta.keys())
    cutoff = utcnow() - timedelta(days=window_days)

    articles = list(
        Collections.news_articles().find(
            {
                "entities_isins": {"$in": eligible_isins},
                "classified": True,
                "severity": "high",
                "fetched_at": {"$gte": cutoff},
            },
            {
                "_id": 1,
                "title": 1,
                "classifier_summary": 1,
                "summary": 1,
                "url": 1,
                "sentiment": 1,
                "severity": 1,
                "themes": 1,
                "entities_isins": 1,
            },
        )
    )
    if not articles:
        return 0

    alerts_log = Collections.alerts_log()
    fired = 0

    for art in articles:
        themes = art.get("themes", []) or []
        # Skip noise-only stories even at high severity.
        if not themes or set(themes).issubset(_NOISE_ONLY):
            continue

        article_id = art["_id"]
        sentiment = art.get("sentiment", "neutral")
        headline = (art.get("title") or "").strip()
        blurb = (
            art.get("classifier_summary") or art.get("summary") or ""
        ).strip()

        # An article can be about several eligible names; alert each once.
        for isin in art.get("entities_isins", []) or []:
            subj = meta.get(isin)
            if subj is None:
                continue  # article tagged a non-eligible name too -- skip it
            if _already_fired(alerts_log, isin, article_id):
                continue

            symbol = subj["symbol"]
            tone = (
                "favourable"
                if sentiment == "positive"
                else "damaging"
                if sentiment == "negative"
                else "material"
            )
            title = f"{symbol}: {tone} news"
            body = headline or blurb or f"High-severity news for {symbol}"
            if blurb and blurb != headline:
                body = f"{headline} — {blurb}" if headline else blurb

            # #80 H2: mirror the #73 fix applied to stop-loss/target evaluators —
            # build + validate the Alert BEFORE the push so a ValidationError
            # (e.g. ISIN length, unknown field) surfaces before any push fires.
            # Then wrap insert_one in try/except: a transient Mongo write failure
            # after a delivered push must not cause the next run to re-push
            # (missing "sent" row → dedup sees nothing → re-fires).
            # Before this fix: push → Alert() → insert_one (unguarded), so any
            # post-push exception left no audit row → duplicate real pushes.
            delivery_status = "sent"
            delivery_error = ""
            ntfy_message_id = ""

            # Build + validate the Alert first (raises ValidationError if bad).
            try:
                alert = Alert(
                    alert_type="news_event",
                    severity="high",
                    channel="ntfy_public_news",
                    isin=isin,
                    symbol=symbol,
                    title=title,
                    body=body,
                    llm_reasoning=blurb,
                    cited_news_ids=[article_id],
                    trigger_data=TriggerData(
                        extras={
                            "sentiment": sentiment,
                            "themes": themes,
                            "url": art.get("url", ""),
                        }
                    ),
                    ntfy_message_id="",
                    delivery_status="sent",
                    delivery_error="",
                )
            except Exception:
                log.exception(
                    "Alert model validation failed for %s (article %s); skipping",
                    isin, article_id,
                )
                continue

            # Push only after the model is validated.
            try:
                resp = push_public(
                    channel="news",
                    title=title,
                    message=body,
                    priority="high",
                    tags=["newspaper"],
                )
                if isinstance(resp, dict):
                    ntfy_message_id = str(resp.get("id", "") or "")
            except Exception as exc:  # push_public raises on transport failure
                log.exception("News-alert ntfy push failed for %s", isin)
                delivery_status = "failed"
                delivery_error = str(exc)

            # Stamp the push result onto the alert before persisting.
            alert.ntfy_message_id = ntfy_message_id
            alert.delivery_status = delivery_status  # type: ignore[assignment]
            alert.delivery_error = delivery_error

            try:
                alerts_log.insert_one(alert.to_mongo())
            except Exception:
                log.exception(
                    "alerts_log insert failed for news_event %s (article %s); "
                    "push was delivered=%s — next run will retry (no sent row)",
                    isin, article_id, delivery_status == "sent",
                )
            fired += 1

    if fired:
        log.info("News alerts fired: %d", fired)
    return fired
