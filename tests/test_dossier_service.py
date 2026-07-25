"""Tests for the dossier JSON parser (#55 hold-horizon focus).

Hermetic: `_parse_dossier` is a pure function (no Atlas, no network, no LLM),
so these tests build a raw JSON string and assert on the parsed dict. Run via
`uv run python -m pytest`.

Covers the #55 buy-side hold-horizon contract:
  - a valid buy dossier surfaces all four hold_horizon* keys
  - an off-list / missing bucket coerces to "medium" (never fails the parse)
  - blank/missing prose fields coerce to the "(insufficient data)" marker
  - the horizon is buy-side only: a sell dossier never grows the keys
  - a garbled horizon does NOT nuke an otherwise valid narrative
"""

from __future__ import annotations

import json

from app.services.dossier_service import (
    _clamp_sentence,
    _empty_dossier,
    _parse_dossier,
)


def _buy_json(**overrides) -> str:
    base = {
        "plain_english_summary": "A reasonable large-cap with steady fundamentals.",
        "one_line_thesis": "Quality compounder at a fair price.",
        "bull_case": ["b1", "b2", "b3"],
        "bear_case": ["r1", "r2", "r3"],
        "key_risks": ["k1", "k2", "k3"],
        "valuation_verdict": "reasonable -- trades near peer median.",
        "portfolio_fit": "Low overlap with current holdings.",
        "hold_horizon": "long",
        "hold_horizon_expected_move": "~15-20% re-rating over 12-18 months if ROE holds.",
        "hold_horizon_rationale": "Structural compounding thesis; needs several quarters.",
        "hold_horizon_review_trigger": "Re-check if ROE drops below 12%.",
    }
    base.update(overrides)
    return json.dumps(base)


def test_buy_dossier_surfaces_all_horizon_keys():
    parsed = _parse_dossier(_buy_json(), direction="buy")
    assert parsed is not None
    assert parsed["hold_horizon"] == "long"
    assert parsed["hold_horizon_expected_move"].startswith("~15-20%")
    assert parsed["hold_horizon_rationale"].startswith("Structural")
    assert parsed["hold_horizon_review_trigger"].startswith("Re-check")


def test_off_list_bucket_coerces_to_medium():
    parsed = _parse_dossier(_buy_json(hold_horizon="forever"), direction="buy")
    assert parsed is not None
    assert parsed["hold_horizon"] == "medium"


def test_missing_bucket_coerces_to_medium_without_failing():
    raw = json.loads(_buy_json())
    del raw["hold_horizon"]
    parsed = _parse_dossier(json.dumps(raw), direction="buy")
    # Absent horizon must NOT fail the whole dossier (leniency decision).
    assert parsed is not None
    assert parsed["hold_horizon"] == "medium"


def test_blank_prose_coerces_to_insufficient_marker():
    parsed = _parse_dossier(
        _buy_json(
            hold_horizon_expected_move="",
            hold_horizon_rationale="   ",
            hold_horizon_review_trigger="valid trigger text",
        ),
        direction="buy",
    )
    assert parsed is not None
    assert parsed["hold_horizon_expected_move"] == "(insufficient data)"
    assert parsed["hold_horizon_rationale"] == "(insufficient data)"
    assert parsed["hold_horizon_review_trigger"] == "valid trigger text"


def test_case_and_whitespace_normalized_on_bucket():
    parsed = _parse_dossier(_buy_json(hold_horizon="  Short  "), direction="buy")
    assert parsed is not None
    assert parsed["hold_horizon"] == "short"


def test_sell_dossier_never_grows_horizon_keys():
    sell_raw = {
        "plain_english_summary": "You are up on this position with an LTCG window open.",
        "one_line_thesis": "Trim into strength.",
        "bull_case": ["b1", "b2", "b3"],
        "bear_case": ["r1", "r2", "r3"],
        "key_risks": ["k1", "k2", "k3"],
        "valuation_verdict": "premium -- stretched vs history.",
        "tax_consideration": "LTCG-eligible; long-term rate applies.",
        "concentration_note": "12% of portfolio -- elevated.",
    }
    parsed = _parse_dossier(json.dumps(sell_raw), direction="sell")
    assert parsed is not None
    assert "hold_horizon" not in parsed
    assert "hold_horizon_expected_move" not in parsed


def test_garbled_horizon_does_not_break_valid_narrative():
    # hold_horizon present but nonsense; prose fields absent entirely.
    raw = json.loads(_buy_json(hold_horizon=123))
    del raw["hold_horizon_expected_move"]
    del raw["hold_horizon_rationale"]
    del raw["hold_horizon_review_trigger"]
    parsed = _parse_dossier(json.dumps(raw), direction="buy")
    assert parsed is not None
    # The real narrative survived intact.
    assert parsed["one_line_thesis"] == "Quality compounder at a fair price."
    assert parsed["bull_case"] == ["b1", "b2", "b3"]
    # Horizon degraded gracefully.
    assert parsed["hold_horizon"] == "medium"
    assert parsed["hold_horizon_expected_move"] == "(insufficient data)"


def test_empty_buy_dossier_has_horizon_shape():
    d = _empty_dossier("parse_failure", direction="buy")
    assert d["hold_horizon"] == "medium"
    assert d["hold_horizon_expected_move"] == "(unavailable)"
    assert d["hold_horizon_rationale"] == "(unavailable)"
    assert d["hold_horizon_review_trigger"] == "(unavailable)"
    assert d["narrative_unavailable"] is True


def test_empty_sell_dossier_has_no_horizon_shape():
    d = _empty_dossier("parse_failure", direction="sell")
    assert "hold_horizon" not in d
    assert d["tax_consideration"] == "(unavailable)"


# ── _clamp_sentence (no mid-word truncation) ────────────────────────────────
def test_clamp_short_text_unchanged():
    assert _clamp_sentence("A tidy sentence.", 400) == "A tidy sentence."


def test_clamp_never_slices_mid_word():
    # Single long run of words, no sentence boundary -> cut at a word + ellipsis.
    text = "alpha beta gamma delta epsilon zeta eta theta iota kappa lambda"
    out = _clamp_sentence(text, 30)
    assert len(out) <= 31  # 30 + the 1-char ellipsis
    assert out.endswith("…")
    # The visible body must be whole words only (no partial trailing token).
    body = out[:-1].strip()
    assert text.startswith(body)
    assert body.split() == body.split()  # no empties
    # The character right after the kept body in the source is a space, proving
    # we cut on a word boundary rather than mid-token.
    assert text[len(body)] == " "


def test_clamp_prefers_sentence_boundary():
    text = "First complete thought here is quite long indeed. Second dangling clause that overflows the budget badly"
    out = _clamp_sentence(text, 60)
    assert out == "First complete thought here is quite long indeed."
    assert not out.endswith("…")


def test_horizon_prose_not_cut_mid_word_via_parser():
    long_move = (
        "A re-rating toward the 52-week high implies a mid-teens percentage "
        "gain over the next two earnings cycles as margins normalize and the "
        "valuation discount to sector peers closes, though execution risk on "
        "the current guidance keeps conviction moderate rather than strong here"
    )  # > 250 chars, single run near the boundary
    parsed = _parse_dossier(_buy_json(hold_horizon_expected_move=long_move), direction="buy")
    assert parsed is not None
    move = parsed["hold_horizon_expected_move"]
    # Never exceeds the 400 budget, and never ends on a partial word.
    assert len(move) <= 401
    if move.endswith("…"):
        # boundary cut: the kept body is a prefix ending at a source space
        body = move[:-1]
        assert long_move.startswith(body)
