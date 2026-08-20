"""Stage 10 direct tests — appeals and irreversible checkpoint finalization."""

import json

import pytest

from tests.direct.test_stage9 import CONTRACT, _prepare


APPEAL_MATCH = "SEEDLING appeal adjudicator"


def _ready(c, vm):
    cid, cp = _prepare(c, vm)
    c.calculate_funding(cp)
    return cid, cp


def _result(decision="UPHOLD", tier="MATERIAL", confidence=8000,
            bps=(6000, 3000, 1000), refs=("1", "2")):
    return {
        "decision": decision,
        "effective_importance_tier": tier,
        "attribution_confidence_bps": confidence,
        "contributors": [
            {"node_id": str(i + 1), "attribution_bps": value}
            for i, value in enumerate(bps)
        ],
        "evidence_refs": list(refs),
        "summary": "Appeal adjudicated against the frozen record.",
    }


def _mock_appeal(vm, result):
    vm.mock_web(r"example\.com", {"body": "public supporting material"})
    vm.mock_llm(APPEAL_MATCH, "```json\n" + json.dumps(result) + "\n```")


def _open(c, ground="IMPACT_UNDERSTATED", refs=None):
    return c.open_appeal("1", "1", ground, refs or ["1", "2"], "Specific challenge.")


def test_open_appeal_canonical_and_history(direct_deploy, direct_vm):
    c = direct_deploy(CONTRACT); _ready(c, direct_vm)
    aid = _open(c)
    rec = json.loads(c.get_appeal(aid))
    assert aid == "1" and rec["status"] == "OPEN" and rec["decision"] == ""
    assert rec["candidate_id"] == "1" and rec["checkpoint_id"] == "1"
    assert json.loads(c.list_candidate_appeals("1", 0, 50))["items"] == [rec]


@pytest.mark.parametrize("mutation", ["candidate", "checkpoint", "ground", "statement"])
def test_open_appeal_validation(direct_deploy, direct_vm, mutation):
    c = direct_deploy(CONTRACT); _ready(c, direct_vm)
    args = ["1", "1", "IMPACT_UNDERSTATED", ["1"], "challenge"]
    if mutation == "candidate": args[0] = "999"
    elif mutation == "checkpoint": args[1] = "999"
    elif mutation == "ground": args[2] = "MADE_UP"
    else: args[4] = ""
    with pytest.raises(Exception): c.open_appeal(*args)


def test_supporting_refs_validation(direct_deploy, direct_vm):
    c = direct_deploy(CONTRACT); _ready(c, direct_vm)
    with pytest.raises(Exception): c.open_appeal("1", "1", "EVIDENCE_OMITTED", ["999"], "x")
    with pytest.raises(Exception): c.open_appeal("1", "1", "EVIDENCE_OMITTED", ["1", "1"], "x")


def test_duplicate_active_appeal_rejected(direct_deploy, direct_vm):
    c = direct_deploy(CONTRACT); _ready(c, direct_vm); _open(c)
    with pytest.raises(Exception): _open(c)


@pytest.mark.parametrize("decision,tier,expected", [
    ("UPHOLD", "MATERIAL", 4000),
    ("MODIFY", "SYSTEMIC", 9000),
    ("VOID", "MATERIAL", 0),
])
def test_appeal_outcomes_and_deterministic_funding(
    direct_deploy, direct_vm, decision, tier, expected,
):
    c = direct_deploy(CONTRACT); _ready(c, direct_vm); aid = _open(c)
    _mock_appeal(direct_vm, _result(decision=decision, tier=tier))
    rec = json.loads(c.evaluate_appeal(aid))
    assert rec["status"] == "RESOLVED" and rec["decision"] == decision
    assert rec["effective_result"]["funding"]["newly_unlocked_funding"] == expected
    preview = json.loads(c.get_funding_preview("1"))
    assert preview["original_funding"]["newly_unlocked_funding"] == 4000
    assert preview["effective_funding"]["newly_unlocked_funding"] == expected


@pytest.mark.parametrize("bad", [
    "not-json",
    json.dumps({"decision": "UPHOLD"}),
    json.dumps({**_result(), "unknown": 1}),
])
def test_malformed_appeal_has_no_partial_write_and_is_retryable(
    direct_deploy, direct_vm, bad,
):
    c = direct_deploy(CONTRACT); _ready(c, direct_vm); aid = _open(c)
    direct_vm.mock_web(r"example\.com", {"body": "source"})
    direct_vm.mock_llm(APPEAL_MATCH, bad)
    with pytest.raises(Exception): c.evaluate_appeal(aid)
    assert json.loads(c.get_appeal(aid))["status"] == "OPEN"
    direct_vm.clear_mocks(); _mock_appeal(direct_vm, _result())
    assert json.loads(c.evaluate_appeal(aid))["status"] == "RESOLVED"


def test_uphold_cannot_mutate_original(direct_deploy, direct_vm):
    c = direct_deploy(CONTRACT); _ready(c, direct_vm); aid = _open(c)
    _mock_appeal(direct_vm, _result(tier="SYSTEMIC"))
    with pytest.raises(Exception): c.evaluate_appeal(aid)
    assert json.loads(c.get_appeal(aid))["status"] == "OPEN"


def test_unresolved_appeal_blocks_finalization(direct_deploy, direct_vm):
    c = direct_deploy(CONTRACT); _ready(c, direct_vm); _open(c)
    with pytest.raises(Exception): c.finalize_checkpoint("1", "1")


@pytest.mark.parametrize("decision,final_status,tier", [
    ("UPHOLD", "FINALIZED", "MATERIAL"),
    ("MODIFY", "FINALIZED", "SYSTEMIC"),
    ("VOID", "VOIDED", "MATERIAL"),
])
def test_finalization_outcomes_and_immutability(
    direct_deploy, direct_vm, decision, final_status, tier,
):
    c = direct_deploy(CONTRACT); _ready(c, direct_vm)
    impact_before = c.get_impact_verdict("1")
    lineage_before = c.get_lineage_verdict("1")
    funding_before = c.get_funding_calculation("1")
    aid = _open(c); _mock_appeal(direct_vm, _result(decision=decision, tier=tier))
    appeal_before = c.evaluate_appeal(aid); direct_vm.clear_mocks()
    assert c.finalize_checkpoint("1", "1") == final_status
    final = json.loads(c.get_checkpoint_finalization("1"))
    assert final["finalized"] and final["effective_appeal_id"] == aid
    assert c.get_impact_verdict("1") == impact_before
    assert c.get_lineage_verdict("1") == lineage_before
    assert c.get_funding_calculation("1") == funding_before
    assert c.get_appeal(aid) == appeal_before
    with pytest.raises(Exception): c.finalize_checkpoint("1", "1")
    with pytest.raises(Exception): c.open_appeal("1", "1", "IMPACT_OVERSTATED", [], "late")
    if decision == "MODIFY": assert json.loads(c.get_candidate("1"))["status"] == "SYSTEMIC"


def test_finalize_without_appeal_and_authorization(
    direct_deploy, direct_vm, direct_alice, direct_owner,
):
    c = direct_deploy(CONTRACT); _ready(c, direct_vm)
    direct_vm.sender = direct_alice
    with pytest.raises(Exception): c.finalize_checkpoint("1", "1")
    direct_vm.sender = direct_owner
    assert c.finalize_checkpoint("1", "1") == "FINALIZED"


def test_pause_blocks_stage10_writes(direct_deploy, direct_vm):
    c = direct_deploy(CONTRACT); _ready(c, direct_vm); c.pause()
    with pytest.raises(Exception): _open(c)
    c.unpause(); aid = _open(c); c.pause()
    with pytest.raises(Exception): c.evaluate_appeal(aid)
    with pytest.raises(Exception): c.finalize_checkpoint("1", "1")


def test_appeal_vocab_and_bounds(direct_deploy):
    c = direct_deploy(CONTRACT); info = json.loads(c.get_protocol_info())
    assert len(info["vocabulary"]["appeal_grounds"]) == 11
    assert info["vocabulary"]["appeal_decisions"] == ["UPHOLD", "MODIFY", "VOID"]
