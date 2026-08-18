"""Stage 2 tests — candidate lifecycle + ObservationPolicy + FundingPolicy.

Direct (in-process) GenVM execution, no node required. Exercises registration
validation, reusable/versioned policy primitives, historical immutability,
creator authorization, monotonic funding caps, BPS bounds, and pause behavior.

Run:  pytest tests/ -v
"""

import json
import pytest

CONTRACT = "contracts/seedling.py"


# --------------------------------------------------------------------------
# helpers — build valid inputs so each test only perturbs what it checks
# --------------------------------------------------------------------------
def _make_obs_policy(c, name="Obs Policy A", types=None, min_cat=2, min_src=3,
                     interval=86400):
    if types is None:
        types = ["OPEN_SOURCE_LIBRARY", "DATASET"]
    return c.create_observation_policy(
        name, types, min_cat, min_src,
        "latent rules", "impact rules", "lineage rules",
        "gaming rules", "substitute rules", interval,
    )


def _make_funding_policy(c, name="Funding Policy A",
                         caps=(100, 500, 1500, 4000, 9000),
                         min_pv=2000, max_gaming=3000, min_attr=6000):
    return c.create_funding_policy(
        name, caps[0], caps[1], caps[2], caps[3], caps[4],
        min_pv, max_gaming, min_attr,
    )


def _register(c, obs="1", fund="1", ctype="OPEN_SOURCE_LIBRARY",
              url="https://example.com/libfoo", name="libfoo"):
    return c.register_candidate(
        name, "A small but foundational library", ctype,
        url, "2020-01-01", True, obs, fund,
    )


def _norm(addr_hex):
    return addr_hex.lower().removeprefix("0x")


# ==========================================================================
# ObservationPolicy
# ==========================================================================
def test_create_observation_policy(direct_deploy, direct_owner):
    c = direct_deploy(CONTRACT)
    pid = _make_obs_policy(c)
    assert pid == "1"

    p = json.loads(c.get_observation_policy(pid))
    assert p["policy_id"] == "1"
    assert p["family_id"] == "1"
    assert p["version"] == 1
    assert p["status"] == "ACTIVE"
    assert p["candidate_types"] == ["OPEN_SOURCE_LIBRARY", "DATASET"]
    assert p["minimum_independent_sources"] == 3
    assert _norm(p["creator"]) == direct_owner.hex()

    info = json.loads(c.get_protocol_info())
    assert info["counts"]["observation_policies"] == 1


def test_observation_policy_rejects_invalid_candidate_type(direct_deploy):
    c = direct_deploy(CONTRACT)
    with pytest.raises(Exception):
        _make_obs_policy(c, types=["OPEN_SOURCE_LIBRARY", "NOT_A_REAL_TYPE"])


def test_observation_policy_rejects_zero_minimum_sources(direct_deploy):
    c = direct_deploy(CONTRACT)
    with pytest.raises(Exception):
        _make_obs_policy(c, min_src=0)


def test_observation_policy_rejects_out_of_range_checkpoint_interval(direct_deploy):
    c = direct_deploy(CONTRACT)
    with pytest.raises(Exception):
        _make_obs_policy(c, interval=1)  # below MIN_CHECKPOINT_INTERVAL


def test_observation_policy_rejects_duplicate_candidate_types(direct_deploy):
    c = direct_deploy(CONTRACT)
    with pytest.raises(Exception):
        _make_obs_policy(c, types=["DATASET", "DATASET"])


def test_observation_policy_versioning_preserves_history(direct_deploy):
    c = direct_deploy(CONTRACT)
    v1 = _make_obs_policy(c, min_src=3)
    assert v1 == "1"

    v2 = c.version_observation_policy(
        v1, "Obs Policy A v2", ["OPEN_SOURCE_LIBRARY"], 2, 5,
        "latent rules 2", "impact rules 2", "lineage rules 2",
        "gaming rules 2", "substitute rules 2", 86400,
    )
    assert v2 == "2"

    # v1 record is immutable and superseded (INACTIVE); its data is unchanged.
    old = json.loads(c.get_observation_policy(v1))
    assert old["version"] == 1
    assert old["minimum_independent_sources"] == 3
    assert old["status"] == "INACTIVE"

    # v2 is the live version.
    new = json.loads(c.get_observation_policy(v2))
    assert new["version"] == 2
    assert new["family_id"] == "1"
    assert new["minimum_independent_sources"] == 5
    assert new["status"] == "ACTIVE"

    hist = json.loads(c.get_observation_policy_history("1"))
    assert hist["family_id"] == "1"
    assert [v["policy_id"] for v in hist["versions"]] == ["1", "2"]
    assert [v["version"] for v in hist["versions"]] == [1, 2]
    assert [v["status"] for v in hist["versions"]] == ["INACTIVE", "ACTIVE"]


def test_observation_policy_version_only_from_latest(direct_deploy):
    c = direct_deploy(CONTRACT)
    _make_obs_policy(c)  # v1 = "1"
    c.version_observation_policy(
        "1", "v2", ["DATASET"], 1, 2, "a", "b", "c", "d", "e", 86400,
    )  # v2 = "2"
    # versioning again from the now-superseded v1 must be rejected
    with pytest.raises(Exception):
        c.version_observation_policy(
            "1", "v3", ["DATASET"], 1, 2, "a", "b", "c", "d", "e", 86400,
        )


def test_observation_policy_only_creator_can_version(direct_deploy, direct_vm,
                                                     direct_owner, direct_alice):
    c = direct_deploy(CONTRACT)
    _make_obs_policy(c)  # creator = owner (default sender)

    direct_vm.sender = direct_alice
    with pytest.raises(Exception):
        c.version_observation_policy(
            "1", "hostile", ["DATASET"], 1, 2, "a", "b", "c", "d", "e", 86400,
        )
    with pytest.raises(Exception):
        c.set_observation_policy_status("1", False)

    # the real creator can toggle status
    direct_vm.sender = direct_owner
    assert c.set_observation_policy_status("1", False) == "INACTIVE"
    assert json.loads(c.get_observation_policy("1"))["status"] == "INACTIVE"
    assert c.set_observation_policy_status("1", True) == "ACTIVE"


# ==========================================================================
# FundingPolicy
# ==========================================================================
def test_create_funding_policy(direct_deploy, direct_owner):
    c = direct_deploy(CONTRACT)
    fid = _make_funding_policy(c)
    assert fid == "1"

    f = json.loads(c.get_funding_policy(fid))
    assert f["funding_policy_id"] == "1"
    assert f["version"] == 1
    assert f["status"] == "ACTIVE"
    assert f["latent_cap_bps"] == 100
    assert f["systemic_cap_bps"] == 9000
    assert _norm(f["creator"]) == direct_owner.hex()


def test_funding_policy_enforces_monotonic_caps(direct_deploy):
    c = direct_deploy(CONTRACT)
    with pytest.raises(Exception):
        # watching < latent violates latent <= watching <= ... <= systemic
        _make_funding_policy(c, caps=(500, 100, 1500, 4000, 9000))


def test_funding_policy_rejects_bps_above_denominator(direct_deploy):
    c = direct_deploy(CONTRACT)
    with pytest.raises(Exception):
        _make_funding_policy(c, caps=(100, 500, 1500, 4000, 10001))


def test_funding_policy_rejects_bps_below_zero(direct_deploy):
    c = direct_deploy(CONTRACT)
    with pytest.raises(Exception):
        _make_funding_policy(c, min_pv=-1)


def test_funding_policy_versioning_preserves_history(direct_deploy):
    c = direct_deploy(CONTRACT)
    v1 = _make_funding_policy(c, caps=(100, 500, 1500, 4000, 9000))
    v2 = c.version_funding_policy(
        v1, "Funding v2", 200, 600, 1600, 4100, 9100, 2500, 2800, 6500,
    )
    assert v2 == "2"

    old = json.loads(c.get_funding_policy(v1))
    assert old["version"] == 1
    assert old["latent_cap_bps"] == 100
    assert old["status"] == "INACTIVE"

    new = json.loads(c.get_funding_policy(v2))
    assert new["version"] == 2
    assert new["family_id"] == "1"
    assert new["latent_cap_bps"] == 200
    assert new["status"] == "ACTIVE"

    hist = json.loads(c.get_funding_policy_history("1"))
    assert [v["funding_policy_id"] for v in hist["versions"]] == ["1", "2"]
    assert [v["status"] for v in hist["versions"]] == ["INACTIVE", "ACTIVE"]


def test_funding_policy_only_creator_can_change_status(direct_deploy, direct_vm,
                                                       direct_alice):
    c = direct_deploy(CONTRACT)
    _make_funding_policy(c)  # creator = owner
    direct_vm.sender = direct_alice
    with pytest.raises(Exception):
        c.set_funding_policy_status("1", False)


# ==========================================================================
# PublicGoodCandidate registration
# ==========================================================================
def test_register_candidate_happy_path(direct_deploy, direct_owner):
    c = direct_deploy(CONTRACT)
    _make_obs_policy(c)      # "1"
    _make_funding_policy(c)  # "1"

    cid = _register(c)
    assert cid == "1"

    cand = json.loads(c.get_candidate(cid))
    assert cand["candidate_id"] == "1"
    assert cand["status"] == "DISCOVERED"
    assert cand["candidate_type"] == "OPEN_SOURCE_LIBRARY"
    assert cand["primary_artifact_url"] == "https://example.com/libfoo"
    assert cand["public_access"] is True
    assert cand["observation_policy_id"] == "1"
    assert cand["funding_policy_id"] == "1"
    assert _norm(cand["submitter"]) == direct_owner.hex()

    info = json.loads(c.get_protocol_info())
    assert info["counts"]["candidates"] == 1


def test_register_candidate_rejects_invalid_type(direct_deploy):
    c = direct_deploy(CONTRACT)
    _make_obs_policy(c)
    _make_funding_policy(c)
    with pytest.raises(Exception):
        _register(c, ctype="NOT_A_TYPE")


def test_register_candidate_rejects_bad_url(direct_deploy):
    c = direct_deploy(CONTRACT)
    _make_obs_policy(c)
    _make_funding_policy(c)
    with pytest.raises(Exception):
        _register(c, url="ftp://example.com/x")     # wrong scheme
    with pytest.raises(Exception):
        _register(c, url="not-a-url")               # no scheme
    with pytest.raises(Exception):
        _register(c, url="https://nodothost/x")     # host without a dot


def test_register_candidate_rejects_missing_policy(direct_deploy):
    c = direct_deploy(CONTRACT)
    _make_obs_policy(c)      # "1"
    _make_funding_policy(c)  # "1"
    with pytest.raises(Exception):
        _register(c, obs="999")   # observation policy does not exist
    with pytest.raises(Exception):
        _register(c, fund="999")  # funding policy does not exist


def test_register_candidate_rejects_inactive_policy(direct_deploy):
    c = direct_deploy(CONTRACT)
    _make_obs_policy(c)      # "1"
    _make_funding_policy(c)  # "1"

    c.set_observation_policy_status("1", False)
    with pytest.raises(Exception):
        _register(c)  # observation policy inactive

    c.set_observation_policy_status("1", True)
    c.set_funding_policy_status("1", False)
    with pytest.raises(Exception):
        _register(c)  # funding policy inactive


def test_register_candidate_no_silent_overwrite(direct_deploy):
    c = direct_deploy(CONTRACT)
    _make_obs_policy(c)
    _make_funding_policy(c)

    first = _register(c, name="libfoo")
    second = _register(c, name="libbar")
    assert first == "1"
    assert second == "2"  # monotonic id, no overwrite

    assert json.loads(c.get_candidate("1"))["name"] == "libfoo"
    assert json.loads(c.get_candidate("2"))["name"] == "libbar"

    listing = json.loads(c.list_candidates(0, 50))
    assert listing["total"] == 2
    assert [i["candidate_id"] for i in listing["items"]] == ["1", "2"]


def test_get_candidate_missing_raises(direct_deploy):
    c = direct_deploy(CONTRACT)
    with pytest.raises(Exception):
        c.get_candidate("1")


# ==========================================================================
# Pause behavior — writes gated, versioning gated
# ==========================================================================
def test_pause_blocks_state_changing_writes(direct_deploy):
    c = direct_deploy(CONTRACT)
    _make_obs_policy(c)      # "1"
    _make_funding_policy(c)  # "1"

    c.pause()
    with pytest.raises(Exception):
        _register(c)
    with pytest.raises(Exception):
        _make_obs_policy(c, name="while paused")
    with pytest.raises(Exception):
        _make_funding_policy(c, name="while paused")

    # views still work while paused
    assert json.loads(c.get_protocol_info())["paused"] is True

    c.unpause()
    assert _register(c) == "1"


# ==========================================================================
# List views — pagination shape and clamping
# ==========================================================================
def test_list_views_shape_and_clamping(direct_deploy):
    c = direct_deploy(CONTRACT)
    _make_obs_policy(c, name="p1")
    _make_obs_policy(c, name="p2")
    _make_funding_policy(c, name="f1")

    obs = json.loads(c.list_observation_policies(0, 999))  # limit clamps to <=50
    assert obs["total"] == 2
    assert len(obs["items"]) == 2
    assert all(i["status"] == "ACTIVE" for i in obs["items"])

    fund = json.loads(c.list_funding_policies(0, 10))
    assert fund["total"] == 1
    assert len(fund["items"]) == 1

    empty = json.loads(c.list_candidates(0, 10))
    assert empty == {"items": [], "total": 0}
