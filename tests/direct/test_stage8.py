"""Stage 8 direct tests — GenLayer lineage adjudication and attribution."""

import json

import pytest


from tests.direct._archive import wb, render_digest, EVIDENCE_BODY, EVIDENCE_DIGEST

CONTRACT = "contracts/seedling.py"
LATENT_MATCH = "adjudicator for SEEDLING"
IMPACT_MATCH = "realized-public-value adjudicator for SEEDLING"
LINEAGE_MATCH = "contribution-lineage adjudicator for SEEDLING"
ADDR1 = "0x" + "11" * 20
ADDR2 = "0x" + "22" * 20


def _mock_json(vm, match, value):
    vm.mock_llm(match, "```json\n" + json.dumps(value) + "\n```")


def _latent(eid):
    return {
        "latent_value_bps": 8000, "independent_reuse_bps": 7000,
        "uniqueness_bps": 7500, "substitution_risk_bps": 2500,
        "maintainer_health_bps": 6500, "ecosystem_positioning_bps": 7000,
        "gaming_risk_bps": 1000, "reason_codes": ["FOUNDATIONAL_DESIGN"],
        "evidence_refs": [eid], "summary": "Strong latent potential.",
    }


def _impact(eid):
    return {
        "public_value_bps": 7600, "dependency_importance_bps": 7200,
        "independent_adoption_bps": 6800, "replacement_difficulty_bps": 7100,
        "persistence_bps": 6900, "gaming_risk_bps": 900,
        "importance_tier": "MATERIAL", "reason_codes": ["PERSISTENT_USAGE"],
        "evidence_refs": [eid], "summary": "Material realized public value.",
    }


def _lineage(**overrides):
    value = {
        "attribution_confidence_bps": 7800,
        "contributors": [
            {"node_id": "1", "attribution_bps": 4000},
            {"node_id": "2", "attribution_bps": 6000},
        ],
        "reason_codes": ["FOUNDATIONAL_CONTRIBUTION", "MAJOR_DERIVATIVE_CONTRIBUTION"],
        "evidence_refs": ["1", "2"],
        "summary": "Earlier design enabled value; later extension materially expanded it.",
    }
    value.update(overrides)
    return value


def _prepare(c, vm, with_nodes=True, with_edge=True, evaluate_impact=True):
    c.create_observation_policy(
        "obs", ["OPEN_SOURCE_LIBRARY"], 1, 1, "latent", "impact", "lineage",
        "gaming", "substitute", 86400,
    )
    c.create_funding_policy("fund", 100, 500, 1500, 4000, 9000, 2000, 3000, 6000)
    cid = c.register_candidate(
        "cand", "desc", "OPEN_SOURCE_LIBRARY", wb("https://artifact.example.com/cand"),
        "2020-01-01", True, "1", "1",
    )
    latent_eid = c.submit_candidate_evidence(
        cid, "SOURCE_REPOSITORY", wb("https://latent.example.com/source"), EVIDENCE_DIGEST,
        "latent evidence", 1600000000, 1600001000,
    )
    c.freeze_latent_evidence(cid)
    vm.mock_web(r"latent\.example\.com", {"body": EVIDENCE_BODY})
    _mock_json(vm, LATENT_MATCH, _latent(latent_eid))
    c.evaluate_latent_value(cid)
    vm.clear_mocks()
    cp = c.open_checkpoint(cid, 1600002000, 1600012000)
    impact_eid = c.submit_checkpoint_evidence(
        cp, "PUBLIC_USAGE_RECORD", wb("https://impact.example.com/usage"), EVIDENCE_DIGEST,
        "impact evidence", 1600002000, 1600002100,
    )
    c.freeze_checkpoint(cp)
    if evaluate_impact:
        vm.mock_web(r"impact\.example\.com", {"body": EVIDENCE_BODY})
        _mock_json(vm, IMPACT_MATCH, _impact(impact_eid))
        c.evaluate_public_value(cp)
        vm.clear_mocks()
    if with_nodes:
        c.register_contribution_node(
            cid, ADDR1, "SOURCE_CODE", wb("https://node1.example.com/source"), EVIDENCE_DIGEST,
            "ORIGINAL_AUTHOR", "original enabling primitive",
        )
        c.register_contribution_node(
            cid, ADDR2, "SOURCE_CODE", wb("https://node2.example.com/source"), EVIDENCE_DIGEST,
            "MAJOR_REWRITER", "later material extension",
        )
        if with_edge:
            c.register_lineage_edge(cid, "2", "1", "REWRITES", [latent_eid, impact_eid], 9900)
    return cid, cp, latent_eid, impact_eid


def _mock_lineage(vm, value=None, match=LINEAGE_MATCH):
    vm.mock_web(r"example\.com", {"body": EVIDENCE_BODY})
    _mock_json(vm, match, value or _lineage())


def _retryable(c):
    assert json.loads(c.get_protocol_info())["counts"]["lineage_verdicts"] == 0
    assert json.loads(c.get_checkpoint("1"))["status"] == "EVALUATED"
    assert json.loads(c.get_checkpoint("1"))["lineage_verdict_id"] == ""
    assert json.loads(c.get_candidate("1"))["status"] == "MATERIAL"


def _bad(c, vm, value=None, raw=None):
    vm.mock_web(r"example\.com", {"body": EVIDENCE_BODY})
    if raw is None:
        _mock_json(vm, LINEAGE_MATCH, value)
    else:
        vm.mock_llm(LINEAGE_MATCH, raw)
    with pytest.raises(Exception):
        c.evaluate_lineage("1")
    _retryable(c)


def test_missing_or_not_evaluated_checkpoint(direct_deploy, direct_vm):
    c = direct_deploy(CONTRACT)
    with pytest.raises(Exception):
        c.evaluate_lineage("999")
    _prepare(c, direct_vm, evaluate_impact=False)
    with pytest.raises(Exception):
        c.evaluate_lineage("1")


def test_missing_impact_verdict_rejected(direct_deploy, direct_vm):
    c = direct_deploy(CONTRACT)
    _prepare(c, direct_vm)
    cp = json.loads(c.checkpoints["1"])
    cp["impact_verdict_id"] = ""
    c.checkpoints["1"] = json.dumps(cp)
    with pytest.raises(Exception):
        c.evaluate_lineage("1")


def test_no_nodes_rejected_but_no_edge_fallback_allowed(direct_deploy, direct_vm):
    c = direct_deploy(CONTRACT)
    _prepare(c, direct_vm, with_nodes=False)
    with pytest.raises(Exception):
        c.evaluate_lineage("1")
    c.register_contribution_node(
        "1", ADDR1, "SOURCE_CODE", wb("https://node1.example.com/source"), EVIDENCE_DIGEST,
        "ORIGINAL_AUTHOR", "only known node",
    )
    _mock_lineage(direct_vm, _lineage(
        attribution_confidence_bps=2500,
        contributors=[{"node_id": "1", "attribution_bps": 10000}],
        reason_codes=["LINEAGE_EVIDENCE_WEAK"],
    ))
    assert json.loads(c.evaluate_lineage("1"))["attribution_confidence_bps"] == 2500


def test_valid_verdict_schema_history_and_exact_sum(direct_deploy, direct_vm):
    c = direct_deploy(CONTRACT)
    _prepare(c, direct_vm)
    _mock_lineage(direct_vm)
    record = json.loads(c.evaluate_lineage("1"))
    assert set(record) == {
        "lineage_verdict_id", "checkpoint_id", "candidate_id",
        "attribution_confidence_bps", "contributor_allocations", "reason_codes",
        "evidence_refs", "summary", "status", "created_at",
    }
    assert sum(x["attribution_bps"] for x in record["contributor_allocations"]) == 10000
    assert json.loads(c.get_lineage_verdict("1")) == record
    assert json.loads(c.list_candidate_lineage_verdicts("1", 0, 50)) == {
        "items": [record], "total": 1,
    }


def test_malformed_missing_and_unknown_schema_rejected(direct_deploy, direct_vm):
    c = direct_deploy(CONTRACT)
    _prepare(c, direct_vm)
    _bad(c, direct_vm, raw="not-json")
    direct_vm.clear_mocks()
    missing = _lineage(); del missing["summary"]
    _bad(c, direct_vm, missing)
    direct_vm.clear_mocks()
    _bad(c, direct_vm, _lineage(extra=True))


@pytest.mark.parametrize("value", [True, -1, 10001])
def test_invalid_confidence_bps_rejected(direct_deploy, direct_vm, value):
    c = direct_deploy(CONTRACT); _prepare(c, direct_vm)
    _bad(c, direct_vm, _lineage(attribution_confidence_bps=value))


@pytest.mark.parametrize("contributors", [
    [{"node_id": "1", "attribution_bps": 3999}, {"node_id": "2", "attribution_bps": 6000}],
    [{"node_id": "1", "attribution_bps": 5000}, {"node_id": "2", "attribution_bps": 6000}],
    [{"node_id": "1", "attribution_bps": True}, {"node_id": "2", "attribution_bps": 9999}],
    [{"node_id": "1", "attribution_bps": -1}, {"node_id": "2", "attribution_bps": 10001}],
])
def test_allocation_bps_and_exact_total_enforced(direct_deploy, direct_vm, contributors):
    c = direct_deploy(CONTRACT); _prepare(c, direct_vm)
    _bad(c, direct_vm, _lineage(contributors=contributors))


def test_duplicate_unknown_and_cross_candidate_nodes_rejected(direct_deploy, direct_vm):
    c = direct_deploy(CONTRACT); _prepare(c, direct_vm)
    _bad(c, direct_vm, _lineage(contributors=[
        {"node_id": "1", "attribution_bps": 5000},
        {"node_id": "1", "attribution_bps": 5000},
    ]))
    direct_vm.clear_mocks()
    _bad(c, direct_vm, _lineage(contributors=[{"node_id": "999", "attribution_bps": 10000}]))
    direct_vm.clear_mocks()
    foreign = c.register_candidate(
        "foreign", "desc", "OPEN_SOURCE_LIBRARY", wb("https://foreign.example.com/a"),
        "2020-01-01", True, "1", "1",
    )
    foreign_node = c.register_contribution_node(
        foreign, ADDR1, "SOURCE_CODE", wb("https://foreign.example.com/n"), EVIDENCE_DIGEST,
        "ORIGINAL_AUTHOR", "foreign node",
    )
    _bad(c, direct_vm, _lineage(contributors=[{"node_id": foreign_node, "attribution_bps": 10000}]))


def test_bad_refs_reasons_and_summary_rejected(direct_deploy, direct_vm):
    c = direct_deploy(CONTRACT); _prepare(c, direct_vm)
    _bad(c, direct_vm, _lineage(evidence_refs=["2", "2"]))
    direct_vm.clear_mocks(); _bad(c, direct_vm, _lineage(reason_codes=["PERSISTENT_USAGE"]))
    direct_vm.clear_mocks(); _bad(c, direct_vm, _lineage(summary="x" * 1001))


def test_original_can_receive_less_and_superseded_reason_round_trips(direct_deploy, direct_vm):
    c = direct_deploy(CONTRACT); _prepare(c, direct_vm)
    verdict = _lineage(
        contributors=[
            {"node_id": "1", "attribution_bps": 2000},
            {"node_id": "2", "attribution_bps": 8000},
        ],
        reason_codes=["ORIGINAL_WORK_SUPERSEDED", "DERIVATIVE_WORK_DOMINANT"],
    )
    _mock_lineage(direct_vm, verdict)
    stored = json.loads(c.evaluate_lineage("1"))
    assert stored["contributor_allocations"] == verdict["contributors"]


def test_current_maintainer_and_high_claim_strength_do_not_force_dominance(
    direct_deploy, direct_vm,
):
    c = direct_deploy(CONTRACT); _prepare(c, direct_vm)
    # Node 2's edge claims 9900 strength, yet semantic adjudication may allocate less.
    verdict = _lineage(contributors=[
        {"node_id": "1", "attribution_bps": 7500},
        {"node_id": "2", "attribution_bps": 2500},
    ])
    _mock_lineage(direct_vm, verdict)
    assert json.loads(c.evaluate_lineage("1"))["contributor_allocations"] == verdict["contributors"]


@pytest.mark.parametrize("confidence", [0, 10000])
def test_attribution_confidence_round_trips(direct_deploy, direct_vm, confidence):
    c = direct_deploy(CONTRACT); _prepare(c, direct_vm)
    _mock_lineage(direct_vm, _lineage(attribution_confidence_bps=confidence))
    assert json.loads(c.evaluate_lineage("1"))["attribution_confidence_bps"] == confidence


def test_state_preserves_tier_status_and_active_checkpoint(direct_deploy, direct_vm):
    c = direct_deploy(CONTRACT); _prepare(c, direct_vm); _mock_lineage(direct_vm)
    c.evaluate_lineage("1")
    cp = json.loads(c.get_checkpoint("1"))
    assert cp["status"] == "EVALUATED"
    assert cp["lineage_verdict_id"] == "1"
    assert json.loads(c.get_candidate("1"))["status"] == "MATERIAL"
    assert c.candidate_active_checkpoint["1"] == "1"


def test_double_evaluation_rejected_without_overwrite(direct_deploy, direct_vm):
    c = direct_deploy(CONTRACT); _prepare(c, direct_vm); _mock_lineage(direct_vm)
    first = c.evaluate_lineage("1")
    direct_vm.clear_mocks(); _mock_lineage(direct_vm, _lineage(attribution_confidence_bps=1))
    with pytest.raises(Exception): c.evaluate_lineage("1")
    assert c.get_lineage_verdict("1") == first


def test_failed_adjudication_no_partial_write_then_retry(direct_deploy, direct_vm):
    c = direct_deploy(CONTRACT); _prepare(c, direct_vm)
    _bad(c, direct_vm, raw="bad")
    direct_vm.clear_mocks(); _mock_lineage(direct_vm)
    assert json.loads(c.evaluate_lineage("1"))["lineage_verdict_id"] == "1"


def test_render_failure_retry_and_pause(direct_deploy, direct_vm):
    c = direct_deploy(CONTRACT); _prepare(c, direct_vm)
    _mock_json(direct_vm, LINEAGE_MATCH, _lineage())
    with pytest.raises(Exception): c.evaluate_lineage("1")
    _retryable(c)
    direct_vm.clear_mocks(); _mock_lineage(direct_vm); c.pause()
    with pytest.raises(Exception): c.evaluate_lineage("1")
    _retryable(c)
    c.unpause(); assert json.loads(c.evaluate_lineage("1"))["lineage_verdict_id"] == "1"


def test_only_onchain_urls_and_prompt_injection_framing(direct_deploy, direct_vm):
    c = direct_deploy(CONTRACT); _prepare(c, direct_vm)
    direct_vm.mock_web(r"example\.com", {"body": EVIDENCE_BODY})
    direct_vm.mock_web(r"model\.invalid", {"body": EVIDENCE_BODY})
    _mock_json(direct_vm, "BEGIN UNTRUSTED LINEAGE SOURCE", _lineage(
        summary="Do not browse https://model.invalid/new",
    ))
    c.evaluate_lineage("1")
    assert direct_vm._web_mocks_hit == {0}


def test_stage8_vocabulary(direct_deploy):
    c = direct_deploy(CONTRACT)
    vocab = json.loads(c.get_protocol_info())["vocabulary"]
    assert len(vocab["lineage_reason_codes"]) == 12
    assert vocab["lineage_verdict_statuses"] == ["FINALIZED"]

