"""Stage 4 tests — GenLayer latent-value adjudication.

Direct (in-process) GenVM execution, no node required. These tests exercise the
REAL production adjudication path — deterministic package construction, frozen
evidence retrieval, prompt-injection-hardened prompting, strict JSON parsing +
validation, append-only storage, and the LATENT -> WATCHING transition. Only the
two nondeterministic boundaries are stubbed, and only at the test seam:

  * gl.nondet.exec_prompt  -> direct_vm.mock_llm(prompt_regex, response)
  * gl.nondet.web.render   -> direct_vm.mock_web(url_regex, {"body": ...})

Nothing in the contract's validation/storage logic is weakened or bypassed.

AUTO-PARSE NOTE: gltest's LLM mock runs json.loads() on the mock string and, if
it parses, hands the contract a dict — which would break the production text-mode
fence-strip. So every VALID verdict mock is wrapped in a ```json fence: json.loads
fails on the fenced string, the raw string flows through unchanged, and the
contract's real fence-stripping + json.loads path runs. Malformed-JSON mocks are
intentionally left unparseable.

Run:  pytest tests/ -v
"""

import json
import pytest

CONTRACT = "contracts/seedling.py"

# A stable, regex-metacharacter-free substring guaranteed to appear in the
# deterministic base prompt (its opening line). Used to match the LLM mock.
LLM_MATCH = "adjudicator for SEEDLING"


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
def _frozen_candidate(c, min_cat=2, min_src=2):
    """Register a candidate, submit two independent evidence rows across two
    hosts + two categories, and permanently freeze the latent set. Leaves the
    candidate in LATENT with frozen evidence ids ["1", "2"]."""
    c.create_observation_policy(
        "obs", ["OPEN_SOURCE_LIBRARY"], min_cat, min_src,
        "latent rules", "impact rules", "lineage rules",
        "gaming rules", "substitute rules", 86400,
    )  # observation policy id "1"
    c.create_funding_policy(
        "fund", 100, 500, 1500, 4000, 9000, 2000, 3000, 6000,
    )  # funding policy id "1"
    c.register_candidate(
        "cand", "a small but foundational library", "OPEN_SOURCE_LIBRARY",
        "https://example.com/artifact", "2020-01-01", True, "1", "1",
    )  # candidate id "1"
    c.submit_candidate_evidence(
        "1", "SOURCE_REPOSITORY", "https://a.example.com/repo", "h1",
        "primary source repository", 1600000000, 1600001000,
    )  # evidence id "1"
    c.submit_candidate_evidence(
        "1", "PACKAGE_REGISTRY", "https://b.example.com/pkg", "h2",
        "package registry listing", 1600000000, 1600001000,
    )  # evidence id "2"
    assert c.freeze_latent_evidence("1") == "LATENT"


def _verdict(**overrides):
    """A schema-valid latent verdict; override any field for negative tests."""
    v = {
        "latent_value_bps": 6200,
        "independent_reuse_bps": 5800,
        "uniqueness_bps": 7000,
        "substitution_risk_bps": 3000,
        "maintainer_health_bps": 6500,
        "ecosystem_positioning_bps": 6000,
        "gaming_risk_bps": 1500,
        "reason_codes": ["EARLY_INDEPENDENT_REUSE", "TECHNICALLY_UNIQUE"],
        "evidence_refs": ["1", "2"],
        "summary": "Early independent reuse across two hosts; few close substitutes.",
    }
    v.update(overrides)
    return v


def _mock_verdict(vm, verdict):
    # Fence valid JSON so gltest's auto-parse fails and the string passes through
    # unchanged, exercising the contract's real fence-strip path.
    vm.mock_llm(LLM_MATCH, "```json\n" + json.dumps(verdict) + "\n```")


def _mock_raw_llm(vm, raw):
    vm.mock_llm(LLM_MATCH, raw)


def _mock_web_ok(vm):
    vm.mock_web(
        r"example\.com",
        {"body": "Public README. Reused by several unrelated, independent projects."},
    )


_ASSESSMENT_FIELDS = {
    "assessment_id", "candidate_id", "latent_value_bps", "independent_reuse_bps",
    "uniqueness_bps", "substitution_risk_bps", "maintainer_health_bps",
    "ecosystem_positioning_bps", "gaming_risk_bps", "reason_codes",
    "evidence_refs", "summary", "status", "created_at",
}


# ==========================================================================
# Pre-conditions
# ==========================================================================
def test_evaluate_requires_existing_candidate(direct_deploy, direct_vm):
    c = direct_deploy(CONTRACT)
    _mock_verdict(direct_vm, _verdict())
    with pytest.raises(Exception):
        c.evaluate_latent_value("999")


def test_evaluate_requires_latent_state(direct_deploy, direct_vm):
    # A DISCOVERED candidate (evidence not yet frozen) must be rejected: it is
    # neither in LATENT nor does it have a frozen set. Proves both the state
    # gate and the frozen-evidence precondition (LATENT is only reachable via a
    # successful freeze).
    c = direct_deploy(CONTRACT)
    c.create_observation_policy(
        "obs", ["OPEN_SOURCE_LIBRARY"], 1, 1,
        "l", "i", "ln", "g", "s", 86400,
    )
    c.create_funding_policy("fund", 100, 500, 1500, 4000, 9000, 2000, 3000, 6000)
    c.register_candidate(
        "cand", "desc", "OPEN_SOURCE_LIBRARY",
        "https://example.com/artifact", "2020-01-01", True, "1", "1",
    )
    c.submit_candidate_evidence(
        "1", "SOURCE_REPOSITORY", "https://a.example.com/repo", "h1",
        "repo", 1600000000, 1600001000,
    )
    _mock_verdict(direct_vm, _verdict(evidence_refs=[]))
    with pytest.raises(Exception):
        c.evaluate_latent_value("1")          # still DISCOVERED, not frozen
    # nothing was stored
    assert json.loads(c.get_protocol_info())["counts"]["latent_assessments"] == 0


# ==========================================================================
# Frozen package + frozen-only retrieval
# ==========================================================================
def test_only_frozen_urls_are_fetched(direct_deploy, direct_vm):
    c = direct_deploy(CONTRACT)
    _frozen_candidate(c)
    # mock 0: a frozen host; mock 1: a decoy host NOT in the frozen evidence set.
    direct_vm.mock_web(r"a\.example\.com", {"body": "frozen source A content"})
    direct_vm.mock_web(r"decoy\.example\.com", {"body": "should never be fetched"})
    _mock_verdict(direct_vm, _verdict())

    c.evaluate_latent_value("1")

    # The frozen url's mock was hit; the decoy was never requested — the leader
    # only ever fetches urls drawn from the frozen evidence set.
    assert 0 in direct_vm._web_mocks_hit
    assert 1 not in direct_vm._web_mocks_hit


def test_survives_web_render_failure(direct_deploy, direct_vm):
    # No web mock at all -> every render raises -> leader substitutes
    # "[content unavailable]" per url and adjudication still completes. Graceful
    # degradation: a retrieval failure does not corrupt or block the verdict.
    c = direct_deploy(CONTRACT)
    _frozen_candidate(c)
    _mock_verdict(direct_vm, _verdict())

    rec = json.loads(c.evaluate_latent_value("1"))
    assert rec["status"] == "FINALIZED"


# ==========================================================================
# Successful adjudication + lifecycle + storage
# ==========================================================================
def test_successful_assessment_stored(direct_deploy, direct_vm):
    c = direct_deploy(CONTRACT)
    _frozen_candidate(c)
    _mock_web_ok(direct_vm)
    _mock_verdict(direct_vm, _verdict())

    rec = json.loads(c.evaluate_latent_value("1"))

    # exactly the 14 canonical fields, nothing more
    assert set(rec.keys()) == _ASSESSMENT_FIELDS
    assert rec["assessment_id"] == "1"
    assert rec["candidate_id"] == "1"
    assert rec["latent_value_bps"] == 6200
    assert rec["independent_reuse_bps"] == 5800
    assert rec["uniqueness_bps"] == 7000
    assert rec["substitution_risk_bps"] == 3000
    assert rec["maintainer_health_bps"] == 6500
    assert rec["ecosystem_positioning_bps"] == 6000
    assert rec["gaming_risk_bps"] == 1500
    assert rec["reason_codes"] == ["EARLY_INDEPENDENT_REUSE", "TECHNICALLY_UNIQUE"]
    assert rec["evidence_refs"] == ["1", "2"]
    assert rec["summary"].startswith("Early independent reuse")
    assert rec["status"] == "FINALIZED"
    assert isinstance(rec["created_at"], int)

    # retrievable via the id view, identical bytes
    assert json.loads(c.get_latent_assessment("1")) == rec
    # counter advanced
    assert json.loads(c.get_protocol_info())["counts"]["latent_assessments"] == 1


def test_lifecycle_latent_to_watching(direct_deploy, direct_vm):
    c = direct_deploy(CONTRACT)
    _frozen_candidate(c)
    _mock_web_ok(direct_vm)
    _mock_verdict(direct_vm, _verdict())

    c.evaluate_latent_value("1")

    cand = json.loads(c.get_candidate("1"))
    assert cand["status"] == "WATCHING"           # LATENT -> WATCHING, not further
    assert cand["latent_assessment_id"] == "1"
    assert "latent_assessed_at" in cand


def test_assessment_history_preserved(direct_deploy, direct_vm):
    c = direct_deploy(CONTRACT)
    _frozen_candidate(c)
    _mock_web_ok(direct_vm)
    _mock_verdict(direct_vm, _verdict())

    c.evaluate_latent_value("1")

    hist = json.loads(c.list_candidate_latent_assessments("1", 0, 50))
    assert hist["total"] == 1
    assert hist["items"][0]["assessment_id"] == "1"
    # the stored record is preserved verbatim and independently addressable
    assert json.loads(c.get_latent_assessment("1"))["assessment_id"] == "1"


def test_evidence_immutable_through_evaluation(direct_deploy, direct_vm):
    c = direct_deploy(CONTRACT)
    _frozen_candidate(c)
    _mock_web_ok(direct_vm)
    _mock_verdict(direct_vm, _verdict())

    c.evaluate_latent_value("1")

    # frozen evidence rows and the freeze snapshot are untouched by adjudication
    assert json.loads(c.get_evidence("1"))["content_hash"] == "h1"
    assert json.loads(c.get_evidence("2"))["content_hash"] == "h2"
    assert json.loads(c.get_evidence("1"))["status"] == "FROZEN"
    snap = json.loads(c.get_latent_evidence_set("1"))
    assert snap["frozen"] is True
    assert snap["evidence_ids"] == ["1", "2"]


def test_bps_boundary_values_accepted(direct_deploy, direct_vm):
    # both extremes (0 and 10000) are valid for every score field
    c = direct_deploy(CONTRACT)
    _frozen_candidate(c)
    _mock_web_ok(direct_vm)
    _mock_verdict(direct_vm, _verdict(
        latent_value_bps=0, independent_reuse_bps=0, uniqueness_bps=0,
        substitution_risk_bps=0, maintainer_health_bps=0,
        ecosystem_positioning_bps=0, gaming_risk_bps=0,
        reason_codes=[], evidence_refs=[],
    ))
    r1 = json.loads(c.evaluate_latent_value("1"))
    assert r1["latent_value_bps"] == 0
    assert r1["reason_codes"] == []
    assert r1["evidence_refs"] == []

    # a second candidate exercises the upper bound
    c.register_candidate(
        "cand2", "another foundational library", "OPEN_SOURCE_LIBRARY",
        "https://example.com/artifact2", "2020-02-02", True, "1", "1",
    )
    c.submit_candidate_evidence(
        "2", "SOURCE_REPOSITORY", "https://c.example.com/repo", "h3",
        "repo", 1600000000, 1600001000,
    )
    c.submit_candidate_evidence(
        "2", "PACKAGE_REGISTRY", "https://d.example.com/pkg", "h4",
        "pkg", 1600000000, 1600001000,
    )
    c.freeze_latent_evidence("2")
    direct_vm.clear_mocks()
    _mock_web_ok(direct_vm)
    _mock_verdict(direct_vm, _verdict(
        latent_value_bps=10000, independent_reuse_bps=10000, uniqueness_bps=10000,
        substitution_risk_bps=10000, maintainer_health_bps=10000,
        ecosystem_positioning_bps=10000, gaming_risk_bps=10000,
        evidence_refs=["3", "4"],
    ))
    r2 = json.loads(c.evaluate_latent_value("2"))
    assert r2["latent_value_bps"] == 10000
    assert r2["gaming_risk_bps"] == 10000


def test_substitution_risk_stored_faithfully(direct_deploy, direct_vm):
    # semantic direction check: a HIGH substitution_risk verdict is stored as-is,
    # never silently inverted. Higher = easier/credible substitutes exist.
    c = direct_deploy(CONTRACT)
    _frozen_candidate(c)
    _mock_web_ok(direct_vm)
    _mock_verdict(direct_vm, _verdict(
        substitution_risk_bps=9200,
        reason_codes=["LIMITED_SUBSTITUTES"],
    ))
    rec = json.loads(c.evaluate_latent_value("1"))
    assert rec["substitution_risk_bps"] == 9200


def test_gaming_risk_stored_faithfully(direct_deploy, direct_vm):
    # semantic direction check: a HIGH gaming_risk verdict citing anti-gaming
    # codes is stored uncorrupted. Higher = metrics likely manipulated.
    c = direct_deploy(CONTRACT)
    _frozen_candidate(c)
    _mock_web_ok(direct_vm)
    _mock_verdict(direct_vm, _verdict(
        gaming_risk_bps=8800,
        reason_codes=["BOT_ACTIVITY_SUSPECTED", "DEPENDENCY_INFLATION_SUSPECTED"],
    ))
    rec = json.loads(c.evaluate_latent_value("1"))
    assert rec["gaming_risk_bps"] == 8800
    assert rec["reason_codes"] == ["BOT_ACTIVITY_SUSPECTED", "DEPENDENCY_INFLATION_SUSPECTED"]


# ==========================================================================
# Strict verdict validation — every deviation rejected
# ==========================================================================
def _expect_rejected(c, direct_vm, mock_setup):
    """Register a bad verdict, assert evaluate raises AND nothing was stored /
    the candidate stays retryable (still LATENT, still frozen, no assessment)."""
    _mock_web_ok(direct_vm)
    mock_setup()
    with pytest.raises(Exception):
        c.evaluate_latent_value("1")
    assert json.loads(c.get_protocol_info())["counts"]["latent_assessments"] == 0
    assert json.loads(c.get_candidate("1"))["status"] == "LATENT"
    assert json.loads(c.list_candidate_latent_assessments("1", 0, 50))["total"] == 0


def test_reject_malformed_json(direct_deploy, direct_vm):
    c = direct_deploy(CONTRACT)
    _frozen_candidate(c)
    _expect_rejected(c, direct_vm, lambda: _mock_raw_llm(direct_vm, "not json at all ((("))


def test_reject_missing_field(direct_deploy, direct_vm):
    c = direct_deploy(CONTRACT)
    _frozen_candidate(c)
    v = _verdict()
    del v["uniqueness_bps"]
    _expect_rejected(c, direct_vm, lambda: _mock_verdict(direct_vm, v))


def test_reject_unknown_field(direct_deploy, direct_vm):
    c = direct_deploy(CONTRACT)
    _frozen_candidate(c)
    _expect_rejected(c, direct_vm, lambda: _mock_verdict(direct_vm, _verdict(bonus_points=5)))


def test_reject_non_integer_bps(direct_deploy, direct_vm):
    c = direct_deploy(CONTRACT)
    _frozen_candidate(c)
    # float
    _expect_rejected(c, direct_vm, lambda: _mock_verdict(direct_vm, _verdict(latent_value_bps=6200.5)))
    # bool must not masquerade as an int
    direct_vm.clear_mocks()
    _expect_rejected(c, direct_vm, lambda: _mock_verdict(direct_vm, _verdict(gaming_risk_bps=True)))
    # numeric string
    direct_vm.clear_mocks()
    _expect_rejected(c, direct_vm, lambda: _mock_verdict(direct_vm, _verdict(uniqueness_bps="7000")))


def test_reject_bps_below_zero(direct_deploy, direct_vm):
    c = direct_deploy(CONTRACT)
    _frozen_candidate(c)
    _expect_rejected(c, direct_vm, lambda: _mock_verdict(direct_vm, _verdict(latent_value_bps=-1)))


def test_reject_bps_above_max(direct_deploy, direct_vm):
    c = direct_deploy(CONTRACT)
    _frozen_candidate(c)
    _expect_rejected(c, direct_vm, lambda: _mock_verdict(direct_vm, _verdict(latent_value_bps=10001)))


def test_reject_unknown_reason_code(direct_deploy, direct_vm):
    # SYSTEMIC_DEPENDENCY is a real protocol positive code but a REALIZED-impact
    # one, deliberately excluded from the latent allowlist — it must be rejected.
    c = direct_deploy(CONTRACT)
    _frozen_candidate(c)
    _expect_rejected(
        c, direct_vm,
        lambda: _mock_verdict(direct_vm, _verdict(reason_codes=["SYSTEMIC_DEPENDENCY"])),
    )
    # a fully made-up code is likewise rejected
    direct_vm.clear_mocks()
    _expect_rejected(
        c, direct_vm,
        lambda: _mock_verdict(direct_vm, _verdict(reason_codes=["TOTALLY_FAKE_CODE"])),
    )


def test_reject_duplicate_reason_code(direct_deploy, direct_vm):
    c = direct_deploy(CONTRACT)
    _frozen_candidate(c)
    _expect_rejected(
        c, direct_vm,
        lambda: _mock_verdict(direct_vm, _verdict(
            reason_codes=["TECHNICALLY_UNIQUE", "TECHNICALLY_UNIQUE"],
        )),
    )


def test_reject_unknown_evidence_ref(direct_deploy, direct_vm):
    c = direct_deploy(CONTRACT)
    _frozen_candidate(c)      # frozen ids are only "1" and "2"
    _expect_rejected(
        c, direct_vm,
        lambda: _mock_verdict(direct_vm, _verdict(evidence_refs=["1", "999"])),
    )


def test_reject_duplicate_evidence_ref(direct_deploy, direct_vm):
    c = direct_deploy(CONTRACT)
    _frozen_candidate(c)
    _expect_rejected(
        c, direct_vm,
        lambda: _mock_verdict(direct_vm, _verdict(evidence_refs=["1", "1"])),
    )


def test_reject_oversized_summary(direct_deploy, direct_vm):
    c = direct_deploy(CONTRACT)
    _frozen_candidate(c)
    _expect_rejected(
        c, direct_vm,
        lambda: _mock_verdict(direct_vm, _verdict(summary="x" * 1001)),
    )


# ==========================================================================
# No partial write / retryability / no double evaluation / pause
# ==========================================================================
def test_no_partial_write_then_retry_succeeds(direct_deploy, direct_vm):
    # A malformed verdict must leave zero state behind, and a subsequent valid
    # adjudication must then succeed — the candidate is fully retryable.
    c = direct_deploy(CONTRACT)
    _frozen_candidate(c)
    _mock_web_ok(direct_vm)

    _mock_raw_llm(direct_vm, "garbage {not valid")
    with pytest.raises(Exception):
        c.evaluate_latent_value("1")
    # nothing persisted, candidate unchanged
    assert json.loads(c.get_protocol_info())["counts"]["latent_assessments"] == 0
    assert json.loads(c.get_candidate("1"))["status"] == "LATENT"

    # swap in a valid verdict and retry
    direct_vm.clear_mocks()
    _mock_web_ok(direct_vm)
    _mock_verdict(direct_vm, _verdict())
    rec = json.loads(c.evaluate_latent_value("1"))
    assert rec["status"] == "FINALIZED"
    assert json.loads(c.get_candidate("1"))["status"] == "WATCHING"


def test_retry_after_adjudication_failure(direct_deploy, direct_vm):
    # A hard adjudication failure (LLM unmocked -> the leader raises) leaves the
    # candidate retryable; mocking the LLM and retrying then succeeds.
    c = direct_deploy(CONTRACT)
    _frozen_candidate(c)
    # no LLM mock registered -> exec_prompt raises inside the leader
    with pytest.raises(Exception):
        c.evaluate_latent_value("1")
    assert json.loads(c.get_protocol_info())["counts"]["latent_assessments"] == 0
    assert json.loads(c.get_candidate("1"))["status"] == "LATENT"

    _mock_verdict(direct_vm, _verdict())
    rec = json.loads(c.evaluate_latent_value("1"))
    assert rec["assessment_id"] == "1"


def test_no_double_evaluation(direct_deploy, direct_vm):
    # After a successful assessment the candidate is WATCHING, so a second
    # evaluate is rejected and can never silently overwrite the first.
    c = direct_deploy(CONTRACT)
    _frozen_candidate(c)
    _mock_web_ok(direct_vm)
    _mock_verdict(direct_vm, _verdict())

    c.evaluate_latent_value("1")
    with pytest.raises(Exception):
        c.evaluate_latent_value("1")

    # still exactly one assessment; history intact
    assert json.loads(c.get_protocol_info())["counts"]["latent_assessments"] == 1
    assert json.loads(c.list_candidate_latent_assessments("1", 0, 50))["total"] == 1


def test_pause_blocks_evaluation(direct_deploy, direct_vm):
    c = direct_deploy(CONTRACT)
    _frozen_candidate(c)
    _mock_web_ok(direct_vm)
    _mock_verdict(direct_vm, _verdict())

    c.pause()
    with pytest.raises(Exception):
        c.evaluate_latent_value("1")
    # views still work while paused
    assert json.loads(c.get_candidate("1"))["status"] == "LATENT"

    c.unpause()
    rec = json.loads(c.evaluate_latent_value("1"))
    assert rec["status"] == "FINALIZED"


def test_latent_vocabulary_exposed(direct_deploy):
    # additive vocabulary: the latent allowlists are introspectable and exclude
    # the three realized-impact positive codes.
    c = direct_deploy(CONTRACT)
    vocab = json.loads(c.get_protocol_info())["vocabulary"]
    assert len(vocab["latent_positive_reason_codes"]) == 9
    assert len(vocab["latent_reason_codes"]) == 21          # 9 positive + 12 anti-gaming
    assert "SYSTEMIC_DEPENDENCY" not in vocab["latent_reason_codes"]
    assert "REPLACEMENT_DIFFICULT" not in vocab["latent_reason_codes"]
    assert "ORIGINAL_CONTRIBUTION_SURVIVES" not in vocab["latent_reason_codes"]
    assert "EARLY_INDEPENDENT_REUSE" in vocab["latent_reason_codes"]
    assert "BOT_ACTIVITY_SUSPECTED" in vocab["latent_reason_codes"]
    assert vocab["latent_assessment_statuses"] == ["FINALIZED"]
