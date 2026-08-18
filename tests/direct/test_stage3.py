"""Stage 3 tests — candidate evidence collection + latent-evidence freeze.

Direct (in-process) GenVM execution, no node required. Exercises evidence
submission validation (type allowlist, URL well-formedness, host normalization,
content-hash / summary bounds, period rules, duplicate protection, per-candidate
cap), the deterministic source-independence gate enforced at freeze time, the
DISCOVERED -> LATENT lifecycle transition, and post-freeze immutability.

No GenLayer adjudication is exercised here — evaluating latent *value* is Stage 4
and is intentionally absent. These tests only cover the deterministic evidence
layer.

Run:  pytest tests/ -v
"""

import json
import pytest

CONTRACT = "contracts/seedling.py"


# --------------------------------------------------------------------------
# helpers — a candidate in DISCOVERED state with an ObservationPolicy whose
# freeze thresholds each test can tune via min_cat / min_src.
# --------------------------------------------------------------------------
def _setup_candidate(c, min_cat=1, min_src=1, types=None):
    if types is None:
        types = ["OPEN_SOURCE_LIBRARY"]
    c.create_observation_policy(
        "obs", types, min_cat, min_src,
        "latent rules", "impact rules", "lineage rules",
        "gaming rules", "substitute rules", 86400,
    )  # observation policy id "1"
    c.create_funding_policy(
        "fund", 100, 500, 1500, 4000, 9000, 2000, 3000, 6000,
    )  # funding policy id "1"
    return c.register_candidate(
        "cand", "a small but foundational library", "OPEN_SOURCE_LIBRARY",
        "https://example.com/artifact", "2020-01-01", True, "1", "1",
    )  # candidate id "1"


def _submit(c, cid="1", stype="SOURCE_REPOSITORY",
            url="https://example.com/e1", chash="hash1",
            summary="a concise evidence summary",
            pstart=1600000000, pend=1600001000):
    return c.submit_candidate_evidence(
        cid, stype, url, chash, summary, pstart, pend,
    )


def _evidence_categories(c):
    return json.loads(c.get_protocol_info())["vocabulary"]["evidence_categories"]


# ==========================================================================
# Submission — happy paths
# ==========================================================================
def test_submit_evidence_happy_path(direct_deploy, direct_owner):
    c = direct_deploy(CONTRACT)
    _setup_candidate(c)

    eid = _submit(c)
    assert eid == "1"

    ev = json.loads(c.get_evidence(eid))
    assert ev["evidence_id"] == "1"
    assert ev["candidate_id"] == "1"
    assert ev["checkpoint_id"] == ""          # canonical null for latent-stage
    assert ev["source_type"] == "SOURCE_REPOSITORY"
    assert ev["source_url"] == "https://example.com/e1"
    assert ev["source_host"] == "example.com"
    assert ev["content_hash"] == "hash1"
    assert ev["status"] == "SUBMITTED"         # derived: candidate not yet frozen
    assert ev["submitter"].lower().removeprefix("0x") == direct_owner.hex()

    listing = json.loads(c.list_candidate_evidence("1", 0, 50))
    assert listing["total"] == 1
    assert listing["frozen"] is False
    assert listing["items"][0]["evidence_id"] == "1"

    info = json.loads(c.get_protocol_info())
    assert info["counts"]["evidence"] == 1


def test_each_valid_evidence_type(direct_deploy):
    c = direct_deploy(CONTRACT)
    _setup_candidate(c)

    cats = _evidence_categories(c)
    assert len(cats) == 14
    for i, cat in enumerate(cats):
        eid = _submit(
            c, stype=cat,
            url="https://ex%d.example.com/p%d" % (i, i),
            chash="hash%d" % i,
        )
        assert json.loads(c.get_evidence(eid))["source_type"] == cat

    assert json.loads(c.list_candidate_evidence("1", 0, 50))["total"] == 14


# ==========================================================================
# Submission — validation failures
# ==========================================================================
def test_invalid_evidence_type(direct_deploy):
    c = direct_deploy(CONTRACT)
    _setup_candidate(c)
    with pytest.raises(Exception):
        _submit(c, stype="NOT_A_REAL_CATEGORY")


def test_malformed_url(direct_deploy):
    c = direct_deploy(CONTRACT)
    _setup_candidate(c)
    with pytest.raises(Exception):
        _submit(c, url="ftp://example.com/x")        # wrong scheme
    with pytest.raises(Exception):
        _submit(c, url="not-a-url")                  # no scheme
    with pytest.raises(Exception):
        _submit(c, url="https://nodothost/x")        # host without a dot
    with pytest.raises(Exception):
        _submit(c, url="https://exa mple.com/x")     # embedded whitespace


def test_normalized_source_host(direct_deploy):
    c = direct_deploy(CONTRACT)
    _setup_candidate(c)
    # userinfo + uppercase + explicit port must all normalize away, while the
    # raw source_url is preserved exactly as submitted.
    eid = _submit(c, url="https://User@EXAMPLE.com:8443/Path")
    ev = json.loads(c.get_evidence(eid))
    assert ev["source_host"] == "example.com"
    assert ev["source_url"] == "https://User@EXAMPLE.com:8443/Path"


def test_missing_content_hash(direct_deploy):
    c = direct_deploy(CONTRACT)
    _setup_candidate(c)
    with pytest.raises(Exception):
        _submit(c, chash="")                         # required
    with pytest.raises(Exception):
        _submit(c, chash="has whitespace")           # must be whitespace-free
    with pytest.raises(Exception):
        _submit(c, chash="x" * 129)                  # exceeds MAX_CONTENT_HASH_LEN (128)


def test_oversized_summary(direct_deploy):
    c = direct_deploy(CONTRACT)
    _setup_candidate(c)
    with pytest.raises(Exception):
        _submit(c, summary="")                       # required
    with pytest.raises(Exception):
        _submit(c, summary="x" * 1001)               # exceeds MAX_SUMMARY_LEN (1000)


def test_invalid_period(direct_deploy):
    c = direct_deploy(CONTRACT)
    _setup_candidate(c)
    with pytest.raises(Exception):
        _submit(c, pstart=1600001000, pend=1600000000)   # start > end
    with pytest.raises(Exception):
        _submit(c, pstart=-1, pend=1600000000)           # negative
    with pytest.raises(Exception):
        _submit(c, pstart=1600000000, pend=4102444800)   # end in the far future


def test_duplicate_evidence(direct_deploy):
    c = direct_deploy(CONTRACT)
    _setup_candidate(c)

    _submit(c, url="https://example.com/e1", chash="hashX")
    # exact same normalized url + content_hash -> rejected
    with pytest.raises(Exception):
        _submit(c, url="https://example.com/e1", chash="hashX")
    # same url, different content_hash -> distinct tuple -> allowed
    assert _submit(c, url="https://example.com/e1", chash="hashY") == "2"
    # case + trailing-slash variant normalizes to the first -> duplicate
    with pytest.raises(Exception):
        _submit(c, url="https://EXAMPLE.com/e1/", chash="hashX")


def test_candidate_evidence_cap(direct_deploy):
    c = direct_deploy(CONTRACT)
    _setup_candidate(c)
    # exactly MAX_EVIDENCE_PER_CANDIDATE (64) succeed; the 65th is rejected.
    for i in range(64):
        _submit(c, url="https://cap%d.example.com/p" % i, chash="h%d" % i)
    assert json.loads(c.list_candidate_evidence("1", 0, 50))["total"] == 64
    with pytest.raises(Exception):
        _submit(c, url="https://cap64.example.com/p", chash="h64")


def test_nonexistent_candidate(direct_deploy):
    c = direct_deploy(CONTRACT)
    _setup_candidate(c)
    with pytest.raises(Exception):
        _submit(c, cid="999")
    with pytest.raises(Exception):
        c.freeze_latent_evidence("999")


def test_inactive_policy_does_not_block_evidence(direct_deploy):
    # A candidate binds an ObservationPolicy version at registration; the exact
    # version's rules govern forever. Deactivating that policy afterward must NOT
    # strand the candidate — submission and freeze still use the bound version.
    c = direct_deploy(CONTRACT)
    _setup_candidate(c, min_cat=1, min_src=1)
    c.set_observation_policy_status("1", False)      # deactivate after binding

    eid = _submit(c)
    assert eid == "1"
    assert c.freeze_latent_evidence("1") == "LATENT"


# ==========================================================================
# Freeze — source-independence gate
# ==========================================================================
def test_freeze_insufficient_evidence(direct_deploy):
    c = direct_deploy(CONTRACT)
    _setup_candidate(c, min_cat=1, min_src=1)
    with pytest.raises(Exception):
        c.freeze_latent_evidence("1")                # zero evidence


def test_freeze_missing_required_category(direct_deploy):
    c = direct_deploy(CONTRACT)
    _setup_candidate(c, min_cat=2, min_src=1)
    # two distinct hosts (satisfies min_src) but only ONE category (< min_cat).
    _submit(c, stype="SOURCE_REPOSITORY", url="https://a.example.com/x", chash="h1")
    _submit(c, stype="SOURCE_REPOSITORY", url="https://b.example.com/y", chash="h2")

    set_view = json.loads(c.get_latent_evidence_set("1"))
    assert set_view["distinct_category_count"] == 1
    assert set_view["requirements_met"] is False
    with pytest.raises(Exception):
        c.freeze_latent_evidence("1")


def test_freeze_insufficient_hosts(direct_deploy):
    c = direct_deploy(CONTRACT)
    _setup_candidate(c, min_cat=1, min_src=3)
    # two distinct categories (satisfies min_cat) but only TWO hosts (< min_src).
    _submit(c, stype="SOURCE_REPOSITORY", url="https://a.example.com/x", chash="h1")
    _submit(c, stype="PACKAGE_REGISTRY", url="https://b.example.com/y", chash="h2")

    assert json.loads(c.get_latent_evidence_set("1"))["distinct_host_count"] == 2
    with pytest.raises(Exception):
        c.freeze_latent_evidence("1")


def test_same_host_different_port_not_independent(direct_deploy):
    # Two submissions on the same host but different ports must count as ONE
    # independent source — a port cannot fake source independence.
    c = direct_deploy(CONTRACT)
    _setup_candidate(c, min_cat=1, min_src=2)
    _submit(c, url="https://example.com:80/a", chash="h1")
    _submit(c, url="https://example.com:8080/b", chash="h2")

    set_view = json.loads(c.get_latent_evidence_set("1"))
    assert set_view["distinct_host_count"] == 1
    assert set_view["distinct_hosts"] == ["example.com"]
    with pytest.raises(Exception):
        c.freeze_latent_evidence("1")               # only 1 distinct host < 2


# ==========================================================================
# Freeze — success, lifecycle transition, and progress view
# ==========================================================================
def test_latent_set_live_progress_before_freeze(direct_deploy):
    c = direct_deploy(CONTRACT)
    _setup_candidate(c, min_cat=2, min_src=2)

    before = json.loads(c.get_latent_evidence_set("1"))
    assert before["frozen"] is False
    assert before["frozen_at"] is None
    assert before["candidate_status"] == "DISCOVERED"
    assert before["requirements_met"] is False

    _submit(c, stype="SOURCE_REPOSITORY", url="https://a.example.com/x", chash="h1")
    _submit(c, stype="PACKAGE_REGISTRY", url="https://b.example.com/y", chash="h2")

    after = json.loads(c.get_latent_evidence_set("1"))
    assert after["frozen"] is False
    assert after["distinct_category_count"] == 2
    assert after["distinct_host_count"] == 2
    assert after["requirements_met"] is True


def test_successful_freeze_and_transition(direct_deploy):
    c = direct_deploy(CONTRACT)
    _setup_candidate(c, min_cat=2, min_src=2)
    _submit(c, stype="SOURCE_REPOSITORY", url="https://a.example.com/x", chash="h1")
    _submit(c, stype="PACKAGE_REGISTRY", url="https://b.example.com/y", chash="h2")

    assert c.freeze_latent_evidence("1") == "LATENT"

    # lifecycle transition DISCOVERED -> LATENT (and nothing further)
    cand = json.loads(c.get_candidate("1"))
    assert cand["status"] == "LATENT"
    assert "latent_frozen_at" in cand

    snap = json.loads(c.get_latent_evidence_set("1"))
    assert snap["frozen"] is True
    assert snap["requirements_met"] is True
    assert snap["evidence_count"] == 2
    assert snap["evidence_ids"] == ["1", "2"]
    assert snap["distinct_category_count"] == 2
    assert snap["distinct_host_count"] == 2
    assert snap["observation_policy_id"] == "1"
    assert snap["candidate_status"] == "LATENT"


def test_post_freeze_invariants(direct_deploy):
    c = direct_deploy(CONTRACT)
    _setup_candidate(c, min_cat=2, min_src=2)
    e1 = _submit(c, stype="SOURCE_REPOSITORY", url="https://a.example.com/x", chash="h1")
    e2 = _submit(c, stype="PACKAGE_REGISTRY", url="https://b.example.com/y", chash="h2")
    c.freeze_latent_evidence("1")

    # evidence status is derived as FROZEN once the owning set is frozen
    assert json.loads(c.get_evidence(e1))["status"] == "FROZEN"
    assert json.loads(c.get_evidence(e2))["status"] == "FROZEN"

    listing = json.loads(c.list_candidate_evidence("1", 0, 50))
    assert listing["frozen"] is True
    assert all(it["status"] == "FROZEN" for it in listing["items"])
    assert listing["total"] == 2

    # no submission after freeze
    with pytest.raises(Exception):
        _submit(c, url="https://c.example.com/z", chash="h3")

    # double freeze rejected
    with pytest.raises(Exception):
        c.freeze_latent_evidence("1")

    # the frozen records are all still present and unchanged
    assert json.loads(c.get_evidence(e1))["content_hash"] == "h1"
    assert json.loads(c.get_evidence(e2))["content_hash"] == "h2"


# ==========================================================================
# Pause behavior — evidence writes and freeze are gated; views still work
# ==========================================================================
def test_pause_blocks_evidence_and_freeze(direct_deploy):
    c = direct_deploy(CONTRACT)
    _setup_candidate(c, min_cat=1, min_src=1)
    _submit(c)                                       # one valid record while live

    c.pause()
    with pytest.raises(Exception):
        _submit(c, url="https://other.example.com/z", chash="hz")
    with pytest.raises(Exception):
        c.freeze_latent_evidence("1")

    # views remain available while paused
    assert json.loads(c.get_latent_evidence_set("1"))["frozen"] is False

    c.unpause()
    assert c.freeze_latent_evidence("1") == "LATENT"
