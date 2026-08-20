"""Stage 12 integration tests — complete deployment-candidate lifecycle."""

import json

import pytest

from tests.direct.test_stage9 import (
    ADDRS, CONTRACT, IMPACT_MATCH, LATENT_MATCH, LINEAGE_MATCH,
    _impact, _latent, _lineage, _mock_json,
)


APPEAL_MATCH = "SEEDLING appeal adjudicator"


def _bootstrap(c, vm):
    c.create_observation_policy(
        "Longitudinal policy", ["OPEN_SOURCE_LIBRARY"], 1, 1,
        "latent", "impact", "lineage", "gaming", "substitutes", 86400,
    )
    c.create_funding_policy(
        "Progressive policy", 100, 500, 1500, 4000, 9000, 2000, 3000, 6000,
    )
    cid = c.register_candidate(
        "Project A", "An obscure foundational primitive", "OPEN_SOURCE_LIBRARY",
        "https://project-a.example.com/source", "2026-01-01", True, "1", "1",
    )
    latent_eid = c.submit_candidate_evidence(
        cid, "SOURCE_REPOSITORY", "https://early.example.com/project-a", "latent-hash",
        "Early public source and downstream experimentation.", 1600000000, 1600001000,
    )
    c.freeze_latent_evidence(cid)
    vm.mock_web(r"early\.example\.com", {"body": "Early independent reuse and unique design."})
    _mock_json(vm, LATENT_MATCH, _latent(latent_eid, 8800))
    latent = json.loads(c.evaluate_latent_value(cid)); vm.clear_mocks()
    assert latent["latent_value_bps"] == 8800

    original = c.register_contribution_node(
        cid, ADDRS[0], "SOURCE_CODE", "https://project-a.example.com/v1", "node-a",
        "ORIGINAL_AUTHOR", "Original 2026 foundational design.",
    )
    fork = c.register_contribution_node(
        cid, ADDRS[1], "SOURCE_CODE", "https://fork-b.example.com/v1", "node-b",
        "FORK_MAINTAINER", "2027 fork extending the original primitive.",
    )
    c.register_lineage_edge(cid, fork, original, "FORKED_FROM", [latent_eid], 9000)
    return cid, latent_eid, original, fork


def _checkpoint(c, vm, start, end, tier, bps=(7000, 3000)):
    cp = c.open_checkpoint("1", start, end)
    eid = c.submit_checkpoint_evidence(
        cp, "PUBLIC_USAGE_RECORD", f"https://impact{cp}.example.com/usage", f"impact-{cp}",
        f"Checkpoint {cp} downstream public usage.", start, start + 100,
    )
    c.freeze_checkpoint(cp)
    vm.mock_web(r"example\.com", {"body": "Bounded public adoption evidence."})
    _mock_json(vm, IMPACT_MATCH, _impact(eid, tier=tier))
    c.evaluate_public_value(cp); vm.clear_mocks()
    vm.mock_web(r"example\.com", {"body": "Historical source and derivative evidence."})
    _mock_json(vm, LINEAGE_MATCH, _lineage(["1", eid], bps=bps))
    lineage = json.loads(c.evaluate_lineage(cp)); vm.clear_mocks()
    funding = json.loads(c.calculate_funding(cp))
    assert lineage["contributor_allocations"][0]["node_id"] == "1"
    return cp, eid, funding


def _appeal_modify(c, vm, cp, eid):
    aid = c.open_appeal(
        "1", cp, "IMPACT_UNDERSTATED", [eid],
        "The frozen evidence supports material rather than emerging importance.",
    )
    result = {
        "decision": "MODIFY", "effective_importance_tier": "MATERIAL",
        "attribution_confidence_bps": 8000,
        "contributors": [
            {"node_id": "1", "attribution_bps": 7000},
            {"node_id": "2", "attribution_bps": 3000},
        ],
        "evidence_refs": ["1", eid],
        "summary": "Material importance supported; original ancestry remains causal.",
    }
    vm.mock_web(r"example\.com", {"body": "Frozen appeal evidence."})
    _mock_json(vm, APPEAL_MATCH, result)
    resolved = json.loads(c.evaluate_appeal(aid)); vm.clear_mocks()
    assert resolved["decision"] == "MODIFY"
    return aid


def test_complete_three_checkpoint_progression_and_forgotten_creator(direct_deploy, direct_vm):
    c = direct_deploy(CONTRACT); _bootstrap(c, direct_vm)

    cp1, _, fund1 = _checkpoint(c, direct_vm, 1600002000, 1600012000, "WATCHING")
    assert fund1["newly_unlocked_funding"] == 500
    c.finalize_checkpoint("1", cp1)

    cp2, eid2, fund2 = _checkpoint(c, direct_vm, 1600012000, 1600022000, "EMERGING")
    assert fund2["previously_recognized_funding"] == 500
    assert fund2["newly_unlocked_funding"] == 1000
    aid = _appeal_modify(c, direct_vm, cp2, eid2)
    effective2 = json.loads(c.get_funding_preview(cp2))["effective_funding"]
    assert effective2["target_cumulative_funding"] == 4000
    assert effective2["newly_unlocked_funding"] == 3500
    assert c.finalize_checkpoint("1", cp2) == "FINALIZED"
    assert json.loads(c.get_checkpoint_finalization(cp2))["effective_appeal_id"] == aid

    cp3, _, fund3 = _checkpoint(c, direct_vm, 1600022000, 1600032000, "SYSTEMIC")
    assert fund3["previously_recognized_funding"] == 4000
    assert fund3["newly_unlocked_funding"] == 5000
    c.finalize_checkpoint("1", cp3)

    summary = json.loads(c.get_candidate_funding_summary("1"))
    assert summary["cumulative_recognized_funding"] == 9000
    assert json.loads(c.get_candidate("1"))["status"] == "SYSTEMIC"
    history = json.loads(c.list_candidate_lineage_verdicts("1", 0, 50))["items"]
    assert len(history) == 3
    assert all(x["contributor_allocations"][0] == {"node_id": "1", "attribution_bps": 7000} for x in history)
    node = json.loads(c.get_contribution_node("1"))
    assert node["contributor"].lower() == ADDRS[0].lower()
    ancestry = json.loads(c.get_lineage_edge("1"))
    assert (ancestry["from_node_id"], ancestry["to_node_id"], ancestry["relationship_type"]) == (
        "2", "1", "FORKED_FROM",
    )


def test_duplicate_candidate_normalization_and_invalid_policy_are_atomic(direct_deploy):
    c = direct_deploy(CONTRACT)
    c.create_observation_policy(
        "obs", ["OPEN_SOURCE_LIBRARY"], 1, 1, "l", "i", "ln", "g", "s", 86400,
    )
    c.create_funding_policy("fund", 100, 500, 1500, 4000, 9000, 0, 10000, 0)
    args = (
        "A", "desc", "OPEN_SOURCE_LIBRARY", "https://PROJECT.example.com/source/",
        "2026", True, "1", "1",
    )
    assert c.register_candidate(*args) == "1"
    with pytest.raises(Exception):
        c.register_candidate(
            "A", "desc", "OPEN_SOURCE_LIBRARY", "https://project.example.com/source",
            "2026", True, "1", "1",
        )
    with pytest.raises(Exception):
        c.register_candidate(
            "bad", "desc", "OPEN_SOURCE_LIBRARY", "https://other.example.com/source",
            "2026", True, "999", "1",
        )
    assert json.loads(c.list_candidates(0, 50))["total"] == 1


def test_malformed_latent_adjudication_is_retryable_without_partial_state(direct_deploy, direct_vm):
    c = direct_deploy(CONTRACT)
    c.create_observation_policy("obs", ["OPEN_SOURCE_LIBRARY"], 1, 1, "l", "i", "n", "g", "s", 86400)
    c.create_funding_policy("fund", 100, 500, 1500, 4000, 9000, 0, 10000, 0)
    c.register_candidate("A", "d", "OPEN_SOURCE_LIBRARY", "https://a.example.com/x", "2026", True, "1", "1")
    eid = c.submit_candidate_evidence("1", "SOURCE_REPOSITORY", "https://e.example.com/x", "h", "s", 1, 2)
    with pytest.raises(Exception):
        c.submit_candidate_evidence("1", "SOURCE_REPOSITORY", "https://e.example.com/x", "h", "s", 1, 2)
    c.freeze_latent_evidence("1")
    with pytest.raises(Exception):
        c.submit_candidate_evidence("1", "SOURCE_REPOSITORY", "https://new.example.com/x", "h2", "s", 1, 2)
    direct_vm.mock_web(r"e\.example\.com", {"body": "evidence"})
    direct_vm.mock_llm(LATENT_MATCH, "not-json")
    with pytest.raises(Exception): c.evaluate_latent_value("1")
    assert json.loads(c.get_candidate("1"))["status"] == "LATENT"
    assert json.loads(c.get_protocol_info())["counts"]["latent_assessments"] == 0
    direct_vm.clear_mocks(); direct_vm.mock_web(r"e\.example\.com", {"body": "evidence"})
    _mock_json(direct_vm, LATENT_MATCH, _latent(eid, 8000))
    assert json.loads(c.evaluate_latent_value("1"))["status"] == "FINALIZED"


def test_complete_lifecycle_replay_and_page_guards(direct_deploy, direct_vm):
    c = direct_deploy(CONTRACT); _bootstrap(c, direct_vm)
    cp, _, _ = _checkpoint(c, direct_vm, 1600002000, 1600012000, "MATERIAL")
    c.finalize_checkpoint("1", cp)
    for call in (
        lambda: c.calculate_funding(cp), lambda: c.evaluate_lineage(cp),
        lambda: c.evaluate_public_value(cp), lambda: c.finalize_checkpoint("1", cp),
        lambda: c.open_appeal("1", cp, "IMPACT_OVERSTATED", [], "late"),
    ):
        with pytest.raises(Exception): call()
    assert len(json.loads(c.list_candidate_lineage_verdicts("1", 0, 99999))["items"]) == 1
