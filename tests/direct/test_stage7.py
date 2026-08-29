"""Stage 7 direct tests — realized public-value GenLayer adjudication."""

import json

import pytest


from tests.direct._archive import wb, render_digest, EVIDENCE_BODY, EVIDENCE_DIGEST

CONTRACT = "contracts/seedling.py"
LATENT_MATCH = "adjudicator for SEEDLING"
IMPACT_MATCH = "realized-public-value adjudicator for SEEDLING"
CP_START = 1600002000
CP_END = 1600012000


def _latent_verdict(eid, score=6200):
    return {
        "latent_value_bps": score,
        "independent_reuse_bps": 5800,
        "uniqueness_bps": 7000,
        "substitution_risk_bps": 3000,
        "maintainer_health_bps": 6500,
        "ecosystem_positioning_bps": 6000,
        "gaming_risk_bps": 1500,
        "reason_codes": ["EARLY_INDEPENDENT_REUSE"],
        "evidence_refs": [eid],
        "summary": "Credible latent potential.",
    }


def _impact_verdict(**overrides):
    verdict = {
        "public_value_bps": 7200,
        "dependency_importance_bps": 6800,
        "independent_adoption_bps": 6400,
        "replacement_difficulty_bps": 7000,
        "persistence_bps": 6600,
        "gaming_risk_bps": 1200,
        "importance_tier": "MATERIAL",
        "reason_codes": ["CROSS_ORG_ADOPTION", "PERSISTENT_USAGE"],
        "evidence_refs": ["2"],
        "summary": "Persistent independent adoption demonstrates material public value.",
    }
    verdict.update(overrides)
    return verdict


def _mock_json(vm, match, value):
    vm.mock_llm(match, "```json\n" + json.dumps(value) + "\n```")


def _prepare(c, vm, latent_score=6200, freeze=True):
    c.create_observation_policy(
        "obs", ["OPEN_SOURCE_LIBRARY"], 1, 1,
        "latent rules", "impact rules", "lineage rules",
        "gaming rules", "substitute rules", 86400,
    )
    c.create_funding_policy(
        "fund", 100, 500, 1500, 4000, 9000, 2000, 3000, 6000,
    )
    cid = c.register_candidate(
        "cand", "candidate description", "OPEN_SOURCE_LIBRARY",
        wb("https://artifact.example.com/cand"), "2020-01-01", True, "1", "1",
    )
    latent_eid = c.submit_candidate_evidence(
        cid, "SOURCE_REPOSITORY", wb("https://latent.example.com/source"),
        EVIDENCE_DIGEST, "latent evidence", 1600000000, 1600001000,
    )
    c.freeze_latent_evidence(cid)
    vm.mock_web(r"latent\.example\.com", {"body": EVIDENCE_BODY})
    _mock_json(vm, LATENT_MATCH, _latent_verdict(latent_eid, latent_score))
    c.evaluate_latent_value(cid)
    vm.clear_mocks()
    checkpoint_id = c.open_checkpoint(cid, CP_START, CP_END)
    checkpoint_eid = c.submit_checkpoint_evidence(
        checkpoint_id, "PUBLIC_USAGE_RECORD", wb("https://impact.example.com/usage"),
        EVIDENCE_DIGEST, "persistent downstream use", CP_START, CP_START + 100,
    )
    if freeze:
        c.freeze_checkpoint(checkpoint_id)
    return cid, checkpoint_id, latent_eid, checkpoint_eid


def _mock_impact(vm, verdict=None, prompt_match=IMPACT_MATCH):
    vm.mock_web(r"impact\.example\.com", {"body": EVIDENCE_BODY})
    _mock_json(vm, prompt_match, verdict or _impact_verdict())


def _assert_retryable(c):
    assert json.loads(c.get_protocol_info())["counts"]["impact_verdicts"] == 0
    assert json.loads(c.get_checkpoint("1"))["status"] == "EVIDENCE_FROZEN"
    assert json.loads(c.get_checkpoint("1"))["impact_verdict_id"] == ""
    assert json.loads(c.get_candidate("1"))["status"] == "WATCHING"
    assert json.loads(c.list_checkpoint_impact_verdicts("1", 0, 50))["total"] == 0


def _expect_bad(c, vm, verdict=None, raw=None):
    vm.mock_web(r"impact\.example\.com", {"body": EVIDENCE_BODY})
    if raw is None:
        _mock_json(vm, IMPACT_MATCH, verdict)
    else:
        vm.mock_llm(IMPACT_MATCH, raw)
    with pytest.raises(Exception):
        c.evaluate_public_value("1")
    _assert_retryable(c)


def test_preconditions_missing_or_unfrozen_checkpoint(direct_deploy, direct_vm):
    c = direct_deploy(CONTRACT)
    with pytest.raises(Exception):
        c.evaluate_public_value("999")
    _prepare(c, direct_vm, freeze=False)
    _mock_impact(direct_vm)
    with pytest.raises(Exception):
        c.evaluate_public_value("1")


def test_missing_latent_assessment_rejected(direct_deploy, direct_vm):
    c = direct_deploy(CONTRACT)
    _prepare(c, direct_vm)
    candidate = json.loads(c.candidates["1"])
    candidate["latent_assessment_id"] = ""
    c.candidates["1"] = json.dumps(candidate)
    _mock_impact(direct_vm)
    with pytest.raises(Exception):
        c.evaluate_public_value("1")
    _assert_retryable(c)


def test_malformed_freeze_snapshot_rejected(direct_deploy, direct_vm):
    c = direct_deploy(CONTRACT)
    _prepare(c, direct_vm)
    c.checkpoint_freeze["1"] = json.dumps({"checkpoint_id": "wrong"})
    _mock_impact(direct_vm)
    with pytest.raises(Exception):
        c.evaluate_public_value("1")
    _assert_retryable(c)


def test_valid_verdict_storage_schema_and_views(direct_deploy, direct_vm):
    c = direct_deploy(CONTRACT)
    _prepare(c, direct_vm)
    _mock_impact(direct_vm)
    record = json.loads(c.evaluate_public_value("1"))
    assert set(record) == {
        "verdict_id", "checkpoint_id", "candidate_id", "public_value_bps",
        "dependency_importance_bps", "independent_adoption_bps",
        "replacement_difficulty_bps", "persistence_bps", "gaming_risk_bps",
        "importance_tier", "reason_codes", "evidence_refs", "summary",
        "status", "created_at",
    }
    assert record["verdict_id"] == "1"
    assert record["status"] == "FINALIZED"
    assert json.loads(c.get_impact_verdict("1")) == record
    history = json.loads(c.list_checkpoint_impact_verdicts("1", 0, 100))
    assert history == {"items": [record], "total": 1}


def test_all_bps_boundaries_accept_zero_and_10000(direct_deploy, direct_vm):
    c = direct_deploy(CONTRACT)
    _prepare(c, direct_vm)
    verdict = _impact_verdict(
        public_value_bps=0,
        dependency_importance_bps=10000,
        independent_adoption_bps=0,
        replacement_difficulty_bps=10000,
        persistence_bps=0,
        gaming_risk_bps=10000,
    )
    _mock_impact(direct_vm, verdict)
    stored = json.loads(c.evaluate_public_value("1"))
    for key in (
        "public_value_bps", "dependency_importance_bps", "independent_adoption_bps",
        "replacement_difficulty_bps", "persistence_bps", "gaming_risk_bps",
    ):
        assert stored[key] == verdict[key]


def test_reject_malformed_json(direct_deploy, direct_vm):
    c = direct_deploy(CONTRACT)
    _prepare(c, direct_vm)
    _expect_bad(c, direct_vm, raw="not-json")


def test_reject_missing_and_unknown_fields(direct_deploy, direct_vm):
    c = direct_deploy(CONTRACT)
    _prepare(c, direct_vm)
    missing = _impact_verdict()
    del missing["persistence_bps"]
    _expect_bad(c, direct_vm, missing)
    direct_vm.clear_mocks()
    _expect_bad(c, direct_vm, _impact_verdict(extra_field=1))


@pytest.mark.parametrize("field,value", [
    ("public_value_bps", True),
    ("dependency_importance_bps", 5.5),
    ("independent_adoption_bps", "6400"),
    ("replacement_difficulty_bps", -1),
    ("gaming_risk_bps", 10001),
])
def test_reject_invalid_bps(direct_deploy, direct_vm, field, value):
    c = direct_deploy(CONTRACT)
    _prepare(c, direct_vm)
    _expect_bad(c, direct_vm, _impact_verdict(**{field: value}))


def test_reject_invalid_importance_tier(direct_deploy, direct_vm):
    c = direct_deploy(CONTRACT)
    _prepare(c, direct_vm)
    _expect_bad(c, direct_vm, _impact_verdict(importance_tier="LATENT"))


def test_reject_unknown_and_duplicate_reason_codes(direct_deploy, direct_vm):
    c = direct_deploy(CONTRACT)
    _prepare(c, direct_vm)
    _expect_bad(c, direct_vm, _impact_verdict(reason_codes=["TECHNICALLY_UNIQUE"]))
    direct_vm.clear_mocks()
    _expect_bad(c, direct_vm, _impact_verdict(
        reason_codes=["PERSISTENT_USAGE", "PERSISTENT_USAGE"],
    ))


def test_reject_unknown_foreign_and_duplicate_evidence_refs(direct_deploy, direct_vm):
    c = direct_deploy(CONTRACT)
    _prepare(c, direct_vm)
    _expect_bad(c, direct_vm, _impact_verdict(evidence_refs=["999"]))
    direct_vm.clear_mocks()
    foreign = c.register_candidate(
        "foreign", "desc", "OPEN_SOURCE_LIBRARY", wb("https://foreign.example.com/a"),
        "2020-01-01", True, "1", "1",
    )
    foreign_eid = c.submit_candidate_evidence(
        foreign, "SOURCE_REPOSITORY", wb("https://foreign.example.com/e"), EVIDENCE_DIGEST,
        "foreign", 1600000000, 1600001000,
    )
    _expect_bad(c, direct_vm, _impact_verdict(evidence_refs=[foreign_eid]))
    direct_vm.clear_mocks()
    _expect_bad(c, direct_vm, _impact_verdict(evidence_refs=["2", "2"]))


def test_reject_oversized_summary(direct_deploy, direct_vm):
    c = direct_deploy(CONTRACT)
    _prepare(c, direct_vm)
    _expect_bad(c, direct_vm, _impact_verdict(summary="x" * 1001))


def test_high_latent_score_can_be_stalled(direct_deploy, direct_vm):
    c = direct_deploy(CONTRACT)
    _prepare(c, direct_vm, latent_score=9000)
    _mock_impact(direct_vm, _impact_verdict(
        public_value_bps=900,
        importance_tier="STALLED",
        reason_codes=["TEMPORARY_HYPE"],
    ))
    record = json.loads(c.evaluate_public_value("1"))
    assert record["importance_tier"] == "STALLED"
    assert json.loads(c.get_candidate("1"))["status"] == "STALLED"


@pytest.mark.parametrize("gaming", [0, 9300])
def test_gaming_risk_round_trips(direct_deploy, direct_vm, gaming):
    c = direct_deploy(CONTRACT)
    _prepare(c, direct_vm)
    reasons = ["BOT_ACTIVITY_SUSPECTED"] if gaming else ["PERSISTENT_USAGE"]
    _mock_impact(direct_vm, _impact_verdict(gaming_risk_bps=gaming, reason_codes=reasons))
    assert json.loads(c.evaluate_public_value("1"))["gaming_risk_bps"] == gaming


def test_replacement_difficulty_direction_preserved(direct_deploy, direct_vm):
    c = direct_deploy(CONTRACT)
    _prepare(c, direct_vm)
    _mock_impact(direct_vm, _impact_verdict(
        replacement_difficulty_bps=9200,
        reason_codes=["REPLACEMENT_DIFFICULT"],
    ))
    assert json.loads(c.evaluate_public_value("1"))["replacement_difficulty_bps"] == 9200


def test_independent_adoption_not_host_derived(direct_deploy, direct_vm):
    c = direct_deploy(CONTRACT)
    _prepare(c, direct_vm)
    _mock_impact(direct_vm, _impact_verdict(
        independent_adoption_bps=1700,
        reason_codes=["COMMON_OWNER_DEPENDENCIES"],
    ))
    assert json.loads(c.evaluate_public_value("1"))["independent_adoption_bps"] == 1700


def test_state_transitions_and_active_checkpoint_retained(direct_deploy, direct_vm):
    c = direct_deploy(CONTRACT)
    _prepare(c, direct_vm)
    _mock_impact(direct_vm, _impact_verdict(importance_tier="EMERGING"))
    c.evaluate_public_value("1")
    checkpoint = json.loads(c.get_checkpoint("1"))
    assert checkpoint["status"] == "EVALUATED"
    assert checkpoint["impact_verdict_id"] == "1"
    assert json.loads(c.get_candidate("1"))["status"] == "EMERGING"
    assert c.candidate_active_checkpoint["1"] == "1"
    with pytest.raises(Exception):
        c.open_checkpoint("1", CP_END, CP_END + 100)


def test_no_double_evaluation_overwrite(direct_deploy, direct_vm):
    c = direct_deploy(CONTRACT)
    _prepare(c, direct_vm)
    _mock_impact(direct_vm)
    first = c.evaluate_public_value("1")
    direct_vm.clear_mocks()
    _mock_impact(direct_vm, _impact_verdict(importance_tier="SYSTEMIC"))
    with pytest.raises(Exception):
        c.evaluate_public_value("1")
    assert c.get_impact_verdict("1") == first
    assert json.loads(c.get_protocol_info())["counts"]["impact_verdicts"] == 1


def test_failed_output_has_no_partial_write_then_retry_succeeds(direct_deploy, direct_vm):
    c = direct_deploy(CONTRACT)
    _prepare(c, direct_vm)
    _expect_bad(c, direct_vm, raw="bad")
    direct_vm.clear_mocks()
    _mock_impact(direct_vm)
    assert json.loads(c.evaluate_public_value("1"))["verdict_id"] == "1"


def test_web_failure_has_no_partial_write_then_retry_succeeds(direct_deploy, direct_vm):
    c = direct_deploy(CONTRACT)
    _prepare(c, direct_vm)
    _mock_json(direct_vm, IMPACT_MATCH, _impact_verdict())
    with pytest.raises(Exception):
        c.evaluate_public_value("1")
    _assert_retryable(c)
    direct_vm.clear_mocks()
    _mock_impact(direct_vm)
    assert json.loads(c.evaluate_public_value("1"))["verdict_id"] == "1"


def test_only_frozen_url_is_rendered_and_no_model_url_followed(direct_deploy, direct_vm):
    c = direct_deploy(CONTRACT)
    _prepare(c, direct_vm)
    direct_vm.mock_web(r"impact\.example\.com", {"body": EVIDENCE_BODY})
    direct_vm.mock_web(r"latent\.example\.com", {"body": EVIDENCE_BODY})
    direct_vm.mock_web(r"model\.example\.com", {"body": EVIDENCE_BODY})
    _mock_json(direct_vm, IMPACT_MATCH, _impact_verdict(
        summary="See https://model.example.com/invented",
    ))
    c.evaluate_public_value("1")
    assert direct_vm._web_mocks_hit == {0}


def test_prompt_contains_untrusted_framing(direct_deploy, direct_vm):
    c = direct_deploy(CONTRACT)
    _prepare(c, direct_vm)
    direct_vm.mock_web(r"impact\.example\.com", {"body": EVIDENCE_BODY})
    _mock_json(direct_vm, "BEGIN UNTRUSTED EVIDENCE", _impact_verdict())
    assert json.loads(c.evaluate_public_value("1"))["verdict_id"] == "1"


def test_pause_blocks_public_value_evaluation(direct_deploy, direct_vm):
    c = direct_deploy(CONTRACT)
    _prepare(c, direct_vm)
    _mock_impact(direct_vm)
    c.pause()
    with pytest.raises(Exception):
        c.evaluate_public_value("1")
    _assert_retryable(c)


def test_stage7_vocabulary_exposed(direct_deploy):
    c = direct_deploy(CONTRACT)
    vocab = json.loads(c.get_protocol_info())["vocabulary"]
    assert vocab["impact_importance_tiers"] == [
        "WATCHING", "EMERGING", "MATERIAL", "SYSTEMIC", "STALLED", "DECLINED",
    ]
    assert len(vocab["impact_positive_reason_codes"]) == 8
    assert len(vocab["impact_reason_codes"]) == 20
    assert vocab["impact_verdict_statuses"] == ["FINALIZED"]
