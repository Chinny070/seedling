"""Stage 1 test foundation — direct (in-process) GenVM execution.

These tests require no running node. The gltest `gltest_direct` pytest plugin
(auto-registered via entry points) provides the `direct_deploy`, `direct_vm`,
`direct_owner`, and `direct_alice` fixtures used below.

They prove the whole toolchain works end-to-end against the Stage 1 scaffold:
deploy -> initialize storage -> read protocol info -> owner-gated control.

Run:  pytest tests/ -v
"""

import json
import pytest

CONTRACT = "contracts/seedling.py"


def test_deploys_and_initializes_storage(direct_deploy):
    c = direct_deploy(CONTRACT)
    info = json.loads(c.get_protocol_info())

    assert info["name"] == "SEEDLING"
    assert info["paused"] is False
    assert info["protocol_version"] == 1
    assert info["spec_version"] == 1

    # every counter starts at zero
    assert set(info["counts"].values()) == {0}
    assert info["counts"]["candidates"] == 0
    assert info["counts"]["appeals"] == 0


def test_owner_is_deployer(direct_deploy, direct_owner):
    c = direct_deploy(CONTRACT)
    info = json.loads(c.get_protocol_info())
    # direct_deploy's default sender is create_address("default_sender"),
    # which is exactly the direct_owner fixture (raw 20-byte address).
    # Normalize both to bare lowercase hex so the check is agnostic to
    # whether as_hex returns a 0x prefix / EIP-55 checksum.
    stored = info["owner"].lower().removeprefix("0x")
    assert stored == direct_owner.hex()


def test_domain_vocabulary_is_complete(direct_deploy):
    c = direct_deploy(CONTRACT)
    vocab = json.loads(c.get_protocol_info())["vocabulary"]

    assert vocab["candidate_statuses"] == [
        "DISCOVERED", "LATENT", "WATCHING", "EMERGING", "MATERIAL",
        "SYSTEMIC", "STALLED", "DECLINED", "ARCHIVED",
    ]
    assert vocab["funding_tiers"] == [
        "LATENT", "WATCHING", "EMERGING", "MATERIAL", "SYSTEMIC",
    ]
    assert len(vocab["candidate_types"]) == 10
    assert len(vocab["evidence_categories"]) == 14
    assert len(vocab["lineage_relationships"]) == 10
    assert len(vocab["positive_reason_codes"]) == 12
    assert len(vocab["anti_gaming_reason_codes"]) == 12
    assert len(vocab["appeal_grounds"]) == 11
    assert vocab["appeal_decisions"] == ["UPHOLD", "MODIFY", "VOID"]


def test_bounds_exposed(direct_deploy):
    c = direct_deploy(CONTRACT)
    bounds = json.loads(c.get_protocol_info())["bounds"]
    assert bounds["bps_denominator"] == 10000
    assert bounds["min_checkpoint_interval"] < bounds["max_checkpoint_interval"]


def test_owner_can_pause_and_unpause(direct_deploy):
    c = direct_deploy(CONTRACT)

    assert c.pause() == "paused"
    assert json.loads(c.get_protocol_info())["paused"] is True

    assert c.unpause() == "unpaused"
    assert json.loads(c.get_protocol_info())["paused"] is False


def test_non_owner_cannot_pause(direct_deploy, direct_vm, direct_alice):
    c = direct_deploy(CONTRACT)
    direct_vm.sender = direct_alice
    with pytest.raises(Exception):
        c.pause()
