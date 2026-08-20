"""Stage 9 direct tests — deterministic progressive dormant funding accounting."""

import json

import pytest


CONTRACT = "contracts/seedling.py"
LATENT_MATCH = "adjudicator for SEEDLING"
IMPACT_MATCH = "realized-public-value adjudicator for SEEDLING"
LINEAGE_MATCH = "contribution-lineage adjudicator for SEEDLING"
ADDRS = ["0x" + part * 20 for part in ("11", "22", "33")]


def _mock_json(vm, match, value):
    vm.mock_llm(match, "```json\n" + json.dumps(value) + "\n```")


def _latent(eid, score=7000):
    return {
        "latent_value_bps": score, "independent_reuse_bps": 6000,
        "uniqueness_bps": 7000, "substitution_risk_bps": 2500,
        "maintainer_health_bps": 6500, "ecosystem_positioning_bps": 6800,
        "gaming_risk_bps": 1000, "reason_codes": ["FOUNDATIONAL_DESIGN"],
        "evidence_refs": [eid], "summary": "Latent context.",
    }


def _impact(eid, tier="MATERIAL", public=7000, gaming=1000):
    return {
        "public_value_bps": public, "dependency_importance_bps": 6800,
        "independent_adoption_bps": 6200, "replacement_difficulty_bps": 7000,
        "persistence_bps": 6500, "gaming_risk_bps": gaming,
        "importance_tier": tier, "reason_codes": ["PERSISTENT_USAGE"],
        "evidence_refs": [eid], "summary": "Realized impact.",
    }


def _lineage(evidence_refs, confidence=8000, bps=(6000, 3000, 1000)):
    return {
        "attribution_confidence_bps": confidence,
        "contributors": [
            {"node_id": str(i + 1), "attribution_bps": amount}
            for i, amount in enumerate(bps)
        ],
        "reason_codes": ["CONTRIBUTION_CAUSALLY_RELEVANT"],
        "evidence_refs": evidence_refs,
        "summary": "Causal contribution allocation.",
    }


def _prepare(
    c, vm, tier="MATERIAL", latent_score=7000, public=7000, gaming=1000,
    confidence=8000, caps=(100, 500, 1500, 4000, 9000),
    allocation_bps=(6000, 3000, 1000),
):
    c.create_observation_policy(
        "obs", ["OPEN_SOURCE_LIBRARY"], 1, 1, "latent", "impact", "lineage",
        "gaming", "substitute", 86400,
    )
    c.create_funding_policy(
        "fund", caps[0], caps[1], caps[2], caps[3], caps[4], 2000, 3000, 6000,
    )
    cid = c.register_candidate(
        "cand", "desc", "OPEN_SOURCE_LIBRARY", "https://artifact.example.com/c",
        "2020-01-01", True, "1", "1",
    )
    latent_eid = c.submit_candidate_evidence(
        cid, "SOURCE_REPOSITORY", "https://latent.example.com/e", "lh", "latent",
        1600000000, 1600001000,
    )
    c.freeze_latent_evidence(cid)
    vm.mock_web(r"latent\.example\.com", {"body": "latent"})
    _mock_json(vm, LATENT_MATCH, _latent(latent_eid, latent_score))
    c.evaluate_latent_value(cid); vm.clear_mocks()
    cp = c.open_checkpoint(cid, 1600002000, 1600012000)
    impact_eid = c.submit_checkpoint_evidence(
        cp, "PUBLIC_USAGE_RECORD", "https://impact.example.com/e", "ih", "impact",
        1600002000, 1600002100,
    )
    c.freeze_checkpoint(cp)
    vm.mock_web(r"impact\.example\.com", {"body": "impact"})
    _mock_json(vm, IMPACT_MATCH, _impact(impact_eid, tier, public, gaming))
    c.evaluate_public_value(cp); vm.clear_mocks()
    for i in range(3):
        c.register_contribution_node(
            cid, ADDRS[i], "SOURCE_CODE", f"https://node{i+1}.example.com/a", f"n{i+1}",
            "ORIGINAL_AUTHOR" if i == 0 else "EXTENSION_AUTHOR", f"node {i+1}",
        )
    c.register_lineage_edge(cid, "2", "1", "EXTENDS", [latent_eid], 9000)
    c.register_lineage_edge(cid, "3", "2", "MAINTAINS", [impact_eid], 9000)
    vm.mock_web(r"example\.com", {"body": "lineage"})
    _mock_json(vm, LINEAGE_MATCH, _lineage([latent_eid, impact_eid], confidence, allocation_bps))
    c.evaluate_lineage(cp); vm.clear_mocks()
    return cid, cp


def _next_checkpoint(c, vm, tier, public=7000, gaming=1000, confidence=8000):
    # Simulate the later Stage 10 resolution boundary solely at the test seam.
    del c.candidate_active_checkpoint["1"]
    first = json.loads(c.checkpoints["1"]); first["status"] = "FINALIZED"
    c.checkpoints["1"] = json.dumps(first)
    cp = c.open_checkpoint("1", 1600012000, 1600022000)
    eid = c.submit_checkpoint_evidence(
        cp, "PUBLIC_USAGE_RECORD", "https://impact2.example.com/e", "ih2", "later impact",
        1600012000, 1600012100,
    )
    c.freeze_checkpoint(cp)
    vm.mock_web(r"impact2\.example\.com", {"body": "later impact"})
    _mock_json(vm, IMPACT_MATCH, _impact(eid, tier, public, gaming))
    c.evaluate_public_value(cp); vm.clear_mocks()
    vm.mock_web(r"example\.com", {"body": "lineage"})
    _mock_json(vm, LINEAGE_MATCH, _lineage(["1", eid], confidence))
    c.evaluate_lineage(cp); vm.clear_mocks()
    return cp


@pytest.mark.parametrize("tier,target", [
    ("WATCHING", 500), ("EMERGING", 1500),
    ("MATERIAL", 4000), ("SYSTEMIC", 9000),
])
def test_tier_targets(direct_deploy, direct_vm, tier, target):
    c = direct_deploy(CONTRACT); _prepare(c, direct_vm, tier=tier)
    rec = json.loads(c.calculate_funding("1"))
    assert rec["target_cumulative_funding"] == target
    assert rec["previously_recognized_funding"] == 0
    assert rec["newly_unlocked_funding"] == target


@pytest.mark.parametrize("tier", ["STALLED", "DECLINED"])
def test_negative_tiers_unlock_nothing(direct_deploy, direct_vm, tier):
    c = direct_deploy(CONTRACT); _prepare(c, direct_vm, tier=tier)
    rec = json.loads(c.calculate_funding("1"))
    assert rec["target_cumulative_funding"] == 0
    assert rec["newly_unlocked_funding"] == 0


def test_high_latent_stalled_does_not_unlock_high_funding(direct_deploy, direct_vm):
    c = direct_deploy(CONTRACT); _prepare(c, direct_vm, tier="STALLED", latent_score=9500)
    assert json.loads(c.calculate_funding("1"))["newly_unlocked_funding"] == 0


def test_canonical_record_and_views(direct_deploy, direct_vm):
    c = direct_deploy(CONTRACT); _prepare(c, direct_vm)
    rec = json.loads(c.calculate_funding("1"))
    assert set(rec) == {
        "funding_calculation_id", "checkpoint_id", "candidate_id", "funding_policy_id",
        "impact_verdict_id", "lineage_verdict_id", "impact_tier",
        "target_cumulative_funding", "previously_recognized_funding",
        "newly_unlocked_funding", "attribution_confidence_bps",
        "contributor_allocations", "status", "created_at",
    }
    assert rec["funding_calculation_id"] == "1"
    assert json.loads(c.get_funding_calculation("1")) == rec
    assert json.loads(c.list_candidate_funding_calculations("1", 0, 50))["items"] == [rec]
    assert json.loads(c.get_candidate_funding_summary("1")) == {
        "candidate_id": "1", "cumulative_recognized_funding": 4000,
        "calculation_count": 1, "latest_funding_calculation_id": "1",
    }


def test_exact_lineage_allocation_and_sum(direct_deploy, direct_vm):
    c = direct_deploy(CONTRACT); _prepare(c, direct_vm)
    rec = json.loads(c.calculate_funding("1"))
    assert [x["amount"] for x in rec["contributor_allocations"]] == [2400, 1200, 400]
    assert sum(x["amount"] for x in rec["contributor_allocations"]) == 4000
    assert [x["attribution_bps"] for x in rec["contributor_allocations"]] == [6000, 3000, 1000]


@pytest.mark.parametrize("amount,tier,caps,expected", [
    (1, "WATCHING", (0, 1, 1, 1, 1), [1, 0, 0]),
    (7, "EMERGING", (0, 1, 7, 7, 7), [5, 2, 0]),
    (101, "MATERIAL", (0, 1, 7, 101, 101), [61, 30, 10]),
])
def test_awkward_rounding_assigns_stable_remainder(
    direct_deploy, direct_vm, amount, tier, caps, expected,
):
    c = direct_deploy(CONTRACT); _prepare(c, direct_vm, tier=tier, caps=caps)
    rec = json.loads(c.calculate_funding("1"))
    assert rec["newly_unlocked_funding"] == amount
    assert [x["amount"] for x in rec["contributor_allocations"]] == expected
    assert sum(expected) == amount


@pytest.mark.parametrize("kwargs", [
    {"public": 1999}, {"gaming": 3001}, {"confidence": 5999},
])
def test_policy_gates_block_new_unlock(direct_deploy, direct_vm, kwargs):
    c = direct_deploy(CONTRACT); _prepare(c, direct_vm, **kwargs)
    assert json.loads(c.calculate_funding("1"))["newly_unlocked_funding"] == 0


def test_bound_historical_policy_used_after_versioning(direct_deploy, direct_vm):
    c = direct_deploy(CONTRACT); _prepare(c, direct_vm)
    new_id = c.version_funding_policy(
        "1", "new", 0, 10, 20, 30, 40, 0, 10000, 0,
    )
    assert new_id == "2"
    rec = json.loads(c.calculate_funding("1"))
    assert rec["funding_policy_id"] == "1"
    assert rec["target_cumulative_funding"] == 4000


def test_incremental_second_checkpoint_and_history(direct_deploy, direct_vm):
    c = direct_deploy(CONTRACT); _prepare(c, direct_vm, tier="EMERGING")
    first = json.loads(c.calculate_funding("1"))
    cp2 = _next_checkpoint(c, direct_vm, "MATERIAL")
    second = json.loads(c.calculate_funding(cp2))
    assert first["newly_unlocked_funding"] == 1500
    assert second["previously_recognized_funding"] == 1500
    assert second["target_cumulative_funding"] == 4000
    assert second["newly_unlocked_funding"] == 2500
    history = json.loads(c.list_candidate_funding_calculations("1", 0, 50))
    assert history["total"] == 2
    assert json.loads(c.get_candidate_funding_summary("1"))["cumulative_recognized_funding"] == 4000


def test_same_or_lower_later_target_never_negative(direct_deploy, direct_vm):
    c = direct_deploy(CONTRACT); _prepare(c, direct_vm, tier="MATERIAL")
    c.calculate_funding("1")
    cp2 = _next_checkpoint(c, direct_vm, "EMERGING")
    second = json.loads(c.calculate_funding(cp2))
    assert second["previously_recognized_funding"] == 4000
    assert second["target_cumulative_funding"] == 4000
    assert second["newly_unlocked_funding"] == 0
    assert all(x["amount"] == 0 for x in second["contributor_allocations"])


def test_duplicate_calculation_rejected(direct_deploy, direct_vm):
    c = direct_deploy(CONTRACT); _prepare(c, direct_vm)
    first = c.calculate_funding("1")
    with pytest.raises(Exception): c.calculate_funding("1")
    assert c.get_funding_calculation("1") == first


def test_missing_impact_verdict_rejected(direct_deploy, direct_vm):
    c = direct_deploy(CONTRACT); _prepare(c, direct_vm)
    cp = json.loads(c.checkpoints["1"]); cp["impact_verdict_id"] = ""
    c.checkpoints["1"] = json.dumps(cp)
    with pytest.raises(Exception): c.calculate_funding("1")


def test_missing_lineage_verdict_rejected(direct_deploy, direct_vm):
    c = direct_deploy(CONTRACT); _prepare(c, direct_vm)
    cp = json.loads(c.checkpoints["1"]); cp["lineage_verdict_id"] = ""
    c.checkpoints["1"] = json.dumps(cp)
    with pytest.raises(Exception): c.calculate_funding("1")


def test_mismatched_verdict_scope_rejected(direct_deploy, direct_vm):
    c = direct_deploy(CONTRACT); _prepare(c, direct_vm)
    impact = json.loads(c.impact_verdicts["1"]); impact["candidate_id"] = "999"
    c.impact_verdicts["1"] = json.dumps(impact)
    with pytest.raises(Exception): c.calculate_funding("1")


def test_invalid_lineage_allocation_rejected(direct_deploy, direct_vm):
    c = direct_deploy(CONTRACT); _prepare(c, direct_vm)
    lineage = json.loads(c.lineage_verdicts["1"])
    lineage["contributor_allocations"][0]["attribution_bps"] = 5999
    c.lineage_verdicts["1"] = json.dumps(lineage)
    with pytest.raises(Exception): c.calculate_funding("1")


def test_pause_and_permissionless_deterministic_call(
    direct_deploy, direct_vm, direct_alice,
):
    c = direct_deploy(CONTRACT); _prepare(c, direct_vm)
    c.pause()
    with pytest.raises(Exception): c.calculate_funding("1")
    c.unpause(); direct_vm.sender = direct_alice
    assert json.loads(c.calculate_funding("1"))["status"] == "CALCULATED"


def test_no_lifecycle_change_or_checkpoint_finalization(direct_deploy, direct_vm):
    c = direct_deploy(CONTRACT); _prepare(c, direct_vm, tier="SYSTEMIC")
    before_candidate = json.loads(c.get_candidate("1"))["status"]
    before_checkpoint = json.loads(c.get_checkpoint("1"))["status"]
    c.calculate_funding("1")
    assert json.loads(c.get_candidate("1"))["status"] == before_candidate == "SYSTEMIC"
    assert json.loads(c.get_checkpoint("1"))["status"] == before_checkpoint == "EVALUATED"
    assert c.candidate_active_checkpoint["1"] == "1"


def test_stage9_vocabulary_and_no_new_nondeterminism(direct_deploy):
    c = direct_deploy(CONTRACT)
    info = json.loads(c.get_protocol_info())
    assert info["vocabulary"]["funding_calculation_statuses"] == ["CALCULATED"]
    assert info["conventions"]["funding_calculation_id"] == "checkpoint_id"
    assert info["conventions"]["funding_rounding"] == "floor_then_remainder_to_ascending_node_id"
