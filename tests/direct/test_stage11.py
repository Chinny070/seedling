"""Stage 11 direct tests — storage bounds, finality, and release safety."""

import json

import pytest

from tests.direct.test_stage2 import _make_funding_policy, _make_obs_policy
from tests.direct.test_stage5 import ADDR_1, ADDR_2, _edge, _node, _one_candidate
from tests.direct.test_stage10 import CONTRACT, _mock_appeal, _open, _ready, _result
from tests.direct._archive import wb, render_digest, EVIDENCE_BODY, EVIDENCE_DIGEST


ADDR_3 = "0x" + "33" * 20


def test_all_large_list_views_clamp_to_protocol_page_limit(direct_deploy):
    c = direct_deploy(CONTRACT); _one_candidate(c)
    for i in range(64):
        _node(c, contributor=ADDR_1, url=wb(f"https://n{i}.example.com/a"), ahash=EVIDENCE_DIGEST)
    page = json.loads(c.list_contribution_nodes("1", 0, 9999))
    assert page["total"] == 64 and len(page["items"]) == 50
    assert [x["node_id"] for x in page["items"][:2]] == ["1", "2"]
    assert len(json.loads(c.list_contribution_nodes("1", 50, 9999))["items"]) == 14
    assert json.loads(c.list_contribution_nodes("1", 999, 9999))["items"] == []


def test_observation_policy_family_is_bounded(direct_deploy):
    c = direct_deploy(CONTRACT); latest = _make_obs_policy(c, min_cat=1, min_src=1)
    for i in range(31):
        latest = c.version_observation_policy(
            latest, f"obs-{i}", ["OPEN_SOURCE_LIBRARY"], 1, 1,
            "latent", "impact", "lineage", "gaming", "substitute", 86400,
        )
    history = json.loads(c.get_observation_policy_history("1"))
    assert len(history["versions"]) == 32
    with pytest.raises(Exception):
        c.version_observation_policy(
            latest, "overflow", ["OPEN_SOURCE_LIBRARY"], 1, 1,
            "latent", "impact", "lineage", "gaming", "substitute", 86400,
        )


def test_funding_policy_family_is_bounded(direct_deploy):
    c = direct_deploy(CONTRACT); latest = _make_funding_policy(c)
    for i in range(31):
        latest = c.version_funding_policy(
            latest, f"fund-{i}", 100, 500, 1500, 4000, 9000, 2000, 3000, 6000,
        )
    assert len(json.loads(c.get_funding_policy_history("1"))["versions"]) == 32
    with pytest.raises(Exception):
        c.version_funding_policy(
            latest, "overflow", 100, 500, 1500, 4000, 9000, 2000, 3000, 6000,
        )


def test_lineage_rejects_longer_directed_cycle(direct_deploy):
    c = direct_deploy(CONTRACT); _one_candidate(c)
    _node(c, contributor=ADDR_1, ahash=EVIDENCE_DIGEST)
    _node(c, contributor=ADDR_2, ahash=EVIDENCE_DIGEST)
    _node(c, contributor=ADDR_3, ahash=EVIDENCE_DIGEST)
    _edge(c, "1", "1", "2", "DERIVED_FROM", [], 8000)
    _edge(c, "1", "2", "3", "EXTENDS", [], 7000)
    with pytest.raises(Exception): _edge(c, "1", "3", "1", "INCORPORATES", [], 6000)
    assert json.loads(c.list_lineage_edges("1", 0, 50))["total"] == 2


def test_effective_modify_drives_summary_without_mutating_original(direct_deploy, direct_vm):
    c = direct_deploy(CONTRACT); _ready(c, direct_vm)
    original = c.get_funding_calculation("1")
    aid = _open(c); _mock_appeal(direct_vm, _result("MODIFY", "SYSTEMIC"))
    c.evaluate_appeal(aid); direct_vm.clear_mocks(); c.finalize_checkpoint("1", "1")
    summary = json.loads(c.get_candidate_funding_summary("1"))
    assert summary["cumulative_recognized_funding"] == 9000
    assert c.get_funding_calculation("1") == original


def test_void_unlocks_zero_and_cannot_be_replayed(direct_deploy, direct_vm):
    c = direct_deploy(CONTRACT); _ready(c, direct_vm)
    aid = _open(c); _mock_appeal(direct_vm, _result("VOID"))
    c.evaluate_appeal(aid); direct_vm.clear_mocks()
    assert json.loads(c.get_funding_preview("1"))["effective_funding"]["newly_unlocked_funding"] == 0
    assert c.finalize_checkpoint("1", "1") == "VOIDED"
    with pytest.raises(Exception): c.finalize_checkpoint("1", "1")
    with pytest.raises(Exception): c.calculate_funding("1")


def test_finalized_checkpoint_rejects_all_adjudication_replays(direct_deploy, direct_vm):
    c = direct_deploy(CONTRACT); _ready(c, direct_vm); c.finalize_checkpoint("1", "1")
    for call in (
        lambda: c.evaluate_public_value("1"),
        lambda: c.evaluate_lineage("1"),
        lambda: c.calculate_funding("1"),
        lambda: c.open_appeal("1", "1", "IMPACT_OVERSTATED", [], "late"),
    ):
        with pytest.raises(Exception): call()


def test_historical_policy_versions_cannot_reprice_finalized_result(direct_deploy, direct_vm):
    c = direct_deploy(CONTRACT); _ready(c, direct_vm); c.finalize_checkpoint("1", "1")
    before = c.get_funding_preview("1")
    c.version_funding_policy("1", "new", 0, 1, 2, 3, 4, 0, 10000, 0)
    c.version_observation_policy(
        "1", "new-obs", ["OPEN_SOURCE_LIBRARY"], 1, 1,
        "x", "x", "x", "x", "x", 86400,
    )
    assert c.get_funding_preview("1") == before


def test_checkpoint_and_appeal_indexes_refuse_growth_past_bounds(direct_deploy, direct_vm):
    c = direct_deploy(CONTRACT); _ready(c, direct_vm)
    c.candidate_checkpoint_ids["1"] = json.dumps([str(i) for i in range(1, 49)])
    del c.candidate_active_checkpoint["1"]
    with pytest.raises(Exception): c.open_checkpoint("1", 1700000000, 1700000100)
    c.candidate_appeal_ids["1"] = json.dumps([str(i) for i in range(1, 33)])
    for i in range(1, 33):
        c.appeals[str(i)] = json.dumps({
            "appeal_id": str(i), "candidate_id": "1", "checkpoint_id": "1",
            "ground": "IMPACT_OVERSTATED", "status": "RESOLVED",
        })
    with pytest.raises(Exception): _open(c, "IMPACT_UNDERSTATED")


def test_release_bounds_are_exposed(direct_deploy):
    c = direct_deploy(CONTRACT); info = json.loads(c.get_protocol_info())
    assert info["bounds"]["max_policy_versions_per_family"] == 32
    assert info["bounds"]["max_list_limit"] == 50
    assert info["conventions"]["lineage_graph"] == "directed_acyclic_claim_graph"
