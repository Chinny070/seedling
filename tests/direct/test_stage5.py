"""Stage 5 tests — contribution nodes + lineage edges (CLAIMS only).

Direct (in-process) GenVM execution, no node required. Exercises the deterministic
contribution-lineage graph: node/edge registration validation, contributor address
canonicalization, duplicate-artifact and duplicate-edge protection, cross-candidate
and self-loop rejection, BPS bounds, evidence-ref validation, append-only
immutability, bounded pagination, pause gating, and — critically — that recording
lineage CLAIMS never changes a candidate's importance state.

These are pure deterministic writes/views: node and edge registration make no
nondeterministic calls, so only the WATCHING-lifecycle test stubs the Stage 4
adjudication seam (to first drive a candidate to WATCHING before adding claims).

Run:  pytest tests/ -v
"""

import json
import pytest

CONTRACT = "contracts/seedling.py"

# Canonical, checksum-agnostic contributor addresses (0x + 40 hex). ADDR_MIXED
# has letters, so its stored .as_hex form is EIP-55 checksummed — compared via
# .lower() throughout. ZERO_ADDR is the null address and must be rejected.
ADDR_1 = "0x" + "11" * 20
ADDR_2 = "0x" + "22" * 20
ADDR_MIXED = "0x" + "ab" * 20
ZERO_ADDR = "0x" + "00" * 20

LLM_MATCH = "adjudicator for SEEDLING"

_NODE_FIELDS = {
    "node_id", "candidate_id", "contributor", "artifact_type", "artifact_url",
    "artifact_hash", "created_at", "role", "summary", "status", "submitter",
}
_EDGE_FIELDS = {
    "edge_id", "candidate_id", "from_node_id", "to_node_id", "relationship_type",
    "evidence_refs", "claimed_strength_bps", "status", "created_at", "submitter",
}
# The exact canonical fields the spec mandates (submitter is an additive extra).
_NODE_CANONICAL = {
    "node_id", "candidate_id", "contributor", "artifact_type", "artifact_url",
    "artifact_hash", "created_at", "role", "summary", "status",
}
_EDGE_CANONICAL = {
    "edge_id", "candidate_id", "from_node_id", "to_node_id", "relationship_type",
    "evidence_refs", "claimed_strength_bps", "status", "created_at",
}


# --------------------------------------------------------------------------
# helpers — build valid inputs so each test only perturbs what it checks
# --------------------------------------------------------------------------
def _norm(addr_hex):
    return addr_hex.lower().removeprefix("0x")


def _policies(c):
    c.create_observation_policy(
        "obs", ["OPEN_SOURCE_LIBRARY"], 1, 1,
        "l", "i", "ln", "g", "s", 86400,
    )  # observation policy "1"
    c.create_funding_policy(
        "fund", 100, 500, 1500, 4000, 9000, 2000, 3000, 6000,
    )  # funding policy "1"


def _reg(c, name="cand", url="https://example.com/artifact"):
    return c.register_candidate(
        name, "desc", "OPEN_SOURCE_LIBRARY",
        url, "2020-01-01", True, "1", "1",
    )


def _evidence(c, cid, host="a.example.com", cat="SOURCE_REPOSITORY", h="e-h1"):
    return c.submit_candidate_evidence(
        cid, cat, "https://" + host + "/x", h,
        "evidence summary", 1600000000, 1600001000,
    )


def _node(c, cid="1", contributor=ADDR_1, atype="SOURCE_CODE",
          url="https://repo.example.com/proj", ahash="hash-aaa",
          role="ORIGINAL_AUTHOR", summary="original implementation"):
    return c.register_contribution_node(
        cid, contributor, atype, url, ahash, role, summary,
    )


def _edge(c, cid="1", frm="1", to="2", rel="FORKED_FROM", refs=None, bps=8000):
    if refs is None:
        refs = []
    return c.register_lineage_edge(cid, frm, to, rel, refs, bps)


def _one_candidate(c):
    """Policies + one DISCOVERED candidate ('1'). Nodes/edges need only that a
    candidate EXISTS — no freeze or evaluation is required to record claims."""
    _policies(c)
    _reg(c)


def _watching_candidate(c, vm):
    """Drive candidate '1' all the way to WATCHING through the real Stage 4 path,
    leaving frozen evidence ids ['1','2']. Used only to prove that later lineage
    claims never move a candidate off WATCHING."""
    c.create_observation_policy(
        "obs", ["OPEN_SOURCE_LIBRARY"], 2, 2,
        "l", "i", "ln", "g", "s", 86400,
    )
    c.create_funding_policy("fund", 100, 500, 1500, 4000, 9000, 2000, 3000, 6000)
    _reg(c)
    _evidence(c, "1", host="a.example.com", cat="SOURCE_REPOSITORY", h="h1")
    _evidence(c, "1", host="b.example.com", cat="PACKAGE_REGISTRY", h="h2")
    assert c.freeze_latent_evidence("1") == "LATENT"
    vm.mock_web(
        r"example\.com",
        {"body": "Public README. Reused by several unrelated, independent projects."},
    )
    verdict = {
        "latent_value_bps": 6200,
        "independent_reuse_bps": 5800,
        "uniqueness_bps": 7000,
        "substitution_risk_bps": 3000,
        "maintainer_health_bps": 6500,
        "ecosystem_positioning_bps": 6000,
        "gaming_risk_bps": 1500,
        "reason_codes": ["EARLY_INDEPENDENT_REUSE", "TECHNICALLY_UNIQUE"],
        "evidence_refs": ["1", "2"],
        "summary": "Early independent reuse; few close substitutes.",
    }
    vm.mock_llm(LLM_MATCH, "```json\n" + json.dumps(verdict) + "\n```")
    assert json.loads(c.evaluate_latent_value("1"))["status"] == "FINALIZED"
    assert json.loads(c.get_candidate("1"))["status"] == "WATCHING"


# ==========================================================================
# ContributionNode — successful registration + canonical record
# ==========================================================================
def test_register_contribution_node_happy_path(direct_deploy, direct_vm, direct_alice):
    c = direct_deploy(CONTRACT)
    _one_candidate(c)

    # submitter (msg.sender) is deliberately distinct from the CLAIMED contributor
    direct_vm.sender = direct_alice
    nid = _node(c, contributor=ADDR_1)
    assert nid == "1"

    rec = json.loads(c.get_contribution_node("1"))
    # exactly the 10 canonical fields plus the additive submitter, nothing more
    assert set(rec.keys()) == _NODE_FIELDS
    assert _NODE_CANONICAL.issubset(rec.keys())
    assert rec["node_id"] == "1"
    assert rec["candidate_id"] == "1"
    assert rec["artifact_type"] == "SOURCE_CODE"
    assert rec["artifact_url"] == "https://repo.example.com/proj"
    assert rec["artifact_hash"] == "hash-aaa"
    assert rec["role"] == "ORIGINAL_AUTHOR"
    assert rec["summary"] == "original implementation"
    assert rec["status"] == "CLAIMED"
    assert isinstance(rec["created_at"], int)
    # contributor stored canonically; submitter is the on-chain caller, not the claim
    assert _norm(rec["contributor"]) == _norm(ADDR_1)
    assert _norm(rec["submitter"]) == direct_alice.hex()
    assert rec["contributor"] != rec["submitter"]

    info = json.loads(c.get_protocol_info())
    assert info["counts"]["contribution_nodes"] == 1


def test_node_contributor_canonicalized(direct_deploy):
    # A mixed-case address is stored in its checksummed .as_hex form; the
    # underlying 20 bytes are preserved (compared case-insensitively).
    c = direct_deploy(CONTRACT)
    _one_candidate(c)
    nid = _node(c, contributor=ADDR_MIXED.upper().replace("0X", "0x"))
    rec = json.loads(c.get_contribution_node(nid))
    assert rec["contributor"].startswith("0x")
    assert _norm(rec["contributor"]) == _norm(ADDR_MIXED)


def test_node_rejects_invalid_candidate(direct_deploy):
    c = direct_deploy(CONTRACT)
    _one_candidate(c)
    with pytest.raises(Exception):
        _node(c, cid="999")


def test_node_rejects_invalid_artifact_type(direct_deploy):
    c = direct_deploy(CONTRACT)
    _one_candidate(c)
    with pytest.raises(Exception):
        _node(c, atype="NOT_A_TYPE")


def test_node_rejects_invalid_artifact_url(direct_deploy):
    c = direct_deploy(CONTRACT)
    _one_candidate(c)
    with pytest.raises(Exception):
        _node(c, url="ftp://repo.example.com/x")     # wrong scheme
    with pytest.raises(Exception):
        _node(c, url="not-a-url")                    # no scheme
    with pytest.raises(Exception):
        _node(c, url="https://nodothost/x")          # host without a dot


def test_node_rejects_bad_artifact_hash(direct_deploy):
    c = direct_deploy(CONTRACT)
    _one_candidate(c)
    with pytest.raises(Exception):
        _node(c, ahash="")                           # missing
    with pytest.raises(Exception):
        _node(c, ahash="has space")                  # whitespace
    with pytest.raises(Exception):
        _node(c, ahash="x" * 129)                    # over MAX_ARTIFACT_HASH_LEN (128)


def test_node_rejects_invalid_role(direct_deploy):
    # "bounded role": an unknown role is rejected (role is an allowlist).
    c = direct_deploy(CONTRACT)
    _one_candidate(c)
    with pytest.raises(Exception):
        _node(c, role="SUPREME_LEADER")


def test_node_rejects_bad_summary(direct_deploy):
    c = direct_deploy(CONTRACT)
    _one_candidate(c)
    with pytest.raises(Exception):
        _node(c, summary="")                         # required
    with pytest.raises(Exception):
        _node(c, summary="x" * 1001)                 # over MAX_SUMMARY_LEN (1000)


def test_node_rejects_zero_and_invalid_contributor(direct_deploy):
    c = direct_deploy(CONTRACT)
    _one_candidate(c)
    with pytest.raises(Exception):
        _node(c, contributor=ZERO_ADDR)              # null address
    with pytest.raises(Exception):
        _node(c, contributor="")                     # empty
    with pytest.raises(Exception):
        _node(c, contributor="0x1234")               # too short
    with pytest.raises(Exception):
        _node(c, contributor="0x" + "zz" * 20)       # not hex


def test_node_duplicate_artifact_rejected_per_candidate(direct_deploy):
    c = direct_deploy(CONTRACT)
    _policies(c)
    _reg(c)                                          # candidate "1"
    _reg(c, name="cand2", url="https://example.com/artifact2")  # candidate "2"

    _node(c, cid="1", url="https://repo.example.com/x", ahash="H1")   # node "1"
    # exact same normalized url + hash on the SAME candidate -> duplicate
    with pytest.raises(Exception):
        _node(c, cid="1", url="https://repo.example.com/x", ahash="H1")
    # a different hash is allowed
    _node(c, cid="1", url="https://repo.example.com/x", ahash="H2")   # node "2"
    # the SAME url + hash on a DIFFERENT candidate is allowed (dedup is per-candidate)
    nid = _node(c, cid="2", url="https://repo.example.com/x", ahash="H1")
    assert nid == "3"


def test_node_append_only_history_and_no_overwrite(direct_deploy):
    c = direct_deploy(CONTRACT)
    _one_candidate(c)
    _node(c, url="https://repo.example.com/a", ahash="HA")   # node "1"
    first = json.loads(c.get_contribution_node("1"))
    _node(c, contributor=ADDR_2, url="https://repo.example.com/b", ahash="HB")  # node "2"

    # node "1" is untouched by the later registration (immutable, no overwrite)
    assert json.loads(c.get_contribution_node("1")) == first

    listing = json.loads(c.list_contribution_nodes("1", 0, 50))
    assert listing["total"] == 2
    assert [n["node_id"] for n in listing["items"]] == ["1", "2"]
    # monotonic ids, distinct records
    assert listing["items"][0]["artifact_hash"] == "HA"
    assert listing["items"][1]["artifact_hash"] == "HB"


def test_node_pagination_bounds(direct_deploy):
    c = direct_deploy(CONTRACT)
    _one_candidate(c)
    for i in range(3):
        _node(c, url="https://repo.example.com/%d" % i, ahash="H%d" % i)

    full = json.loads(c.list_contribution_nodes("1", 0, 999))  # clamps, no error
    assert full["total"] == 3
    assert len(full["items"]) == 3

    page = json.loads(c.list_contribution_nodes("1", 1, 1))
    assert page["total"] == 3
    assert [n["node_id"] for n in page["items"]] == ["2"]

    beyond = json.loads(c.list_contribution_nodes("1", 99, 10))
    assert beyond == {"items": [], "total": 3}


# ==========================================================================
# LineageEdge — successful registration + canonical record
# ==========================================================================
def test_register_lineage_edge_happy_path(direct_deploy, direct_vm, direct_alice):
    c = direct_deploy(CONTRACT)
    _policies(c)
    _reg(c)                                          # candidate "1"
    _evidence(c, "1", host="a.example.com", h="e1")  # evidence "1"
    _evidence(c, "1", host="b.example.com", h="e2")  # evidence "2"
    _node(c, url="https://repo.example.com/a", ahash="na")             # node "1"
    _node(c, contributor=ADDR_2, url="https://repo.example.com/b", ahash="nb")  # node "2"

    direct_vm.sender = direct_alice
    eid = _edge(c, "1", "1", "2", "FORKED_FROM", ["1", "2"], 8000)
    assert eid == "1"

    rec = json.loads(c.get_lineage_edge("1"))
    assert set(rec.keys()) == _EDGE_FIELDS
    assert _EDGE_CANONICAL.issubset(rec.keys())
    assert rec["edge_id"] == "1"
    assert rec["candidate_id"] == "1"
    assert rec["from_node_id"] == "1"
    assert rec["to_node_id"] == "2"
    assert rec["relationship_type"] == "FORKED_FROM"
    assert rec["evidence_refs"] == ["1", "2"]
    assert rec["claimed_strength_bps"] == 8000
    assert rec["status"] == "CLAIMED"
    assert isinstance(rec["created_at"], int)
    assert _norm(rec["submitter"]) == direct_alice.hex()

    info = json.loads(c.get_protocol_info())
    assert info["counts"]["lineage_edges"] == 1


def test_edge_empty_evidence_refs_allowed(direct_deploy):
    c = direct_deploy(CONTRACT)
    _one_candidate(c)
    _node(c, ahash="na")                             # node "1"
    _node(c, contributor=ADDR_2, ahash="nb")         # node "2"
    eid = _edge(c, "1", "1", "2", "EXTENDS", [], 0)  # no supporting evidence; bps floor
    rec = json.loads(c.get_lineage_edge(eid))
    assert rec["evidence_refs"] == []
    assert rec["claimed_strength_bps"] == 0


def test_edge_bps_upper_bound_accepted(direct_deploy):
    c = direct_deploy(CONTRACT)
    _one_candidate(c)
    _node(c, ahash="na")                             # node "1"
    _node(c, contributor=ADDR_2, ahash="nb")         # node "2"
    eid = _edge(c, "1", "1", "2", "DERIVED_FROM", [], 10000)
    assert json.loads(c.get_lineage_edge(eid))["claimed_strength_bps"] == 10000


def test_edge_rejects_invalid_relationship_type(direct_deploy):
    c = direct_deploy(CONTRACT)
    _one_candidate(c)
    _node(c, ahash="na")
    _node(c, contributor=ADDR_2, ahash="nb")
    with pytest.raises(Exception):
        _edge(c, "1", "1", "2", "IS_COOL", [], 5000)


def test_edge_rejects_missing_from_node(direct_deploy):
    c = direct_deploy(CONTRACT)
    _one_candidate(c)
    _node(c, ahash="na")                             # node "1"
    with pytest.raises(Exception):
        _edge(c, "1", "999", "1", "FORKED_FROM", [], 5000)


def test_edge_rejects_missing_to_node(direct_deploy):
    c = direct_deploy(CONTRACT)
    _one_candidate(c)
    _node(c, ahash="na")                             # node "1"
    with pytest.raises(Exception):
        _edge(c, "1", "1", "999", "FORKED_FROM", [], 5000)


def test_edge_rejects_cross_candidate_node(direct_deploy):
    # A node belonging to another candidate cannot be an endpoint.
    c = direct_deploy(CONTRACT)
    _policies(c)
    _reg(c)                                          # candidate "1"
    _reg(c, name="cand2", url="https://example.com/artifact2")  # candidate "2"
    _node(c, cid="1", ahash="na")                    # node "1" -> candidate "1"
    _node(c, cid="2", contributor=ADDR_2, ahash="nb")  # node "2" -> candidate "2"
    with pytest.raises(Exception):
        _edge(c, "1", "1", "2", "FORKED_FROM", [], 5000)  # to-node is cross-candidate


def test_edge_rejects_self_loop(direct_deploy):
    c = direct_deploy(CONTRACT)
    _one_candidate(c)
    _node(c, ahash="na")                             # node "1"
    with pytest.raises(Exception):
        _edge(c, "1", "1", "1", "FORKED_FROM", [], 5000)


def test_edge_rejects_duplicate_identical_edge(direct_deploy):
    c = direct_deploy(CONTRACT)
    _one_candidate(c)
    _node(c, ahash="na")                             # node "1"
    _node(c, contributor=ADDR_2, ahash="nb")         # node "2"
    _edge(c, "1", "1", "2", "FORKED_FROM", [], 5000)  # edge "1"
    # exact same (candidate, from, to, relationship) -> duplicate rejected
    with pytest.raises(Exception):
        _edge(c, "1", "1", "2", "FORKED_FROM", [], 9999)
    # a DIFFERENT relationship between the same nodes is a distinct claim -> allowed
    eid = _edge(c, "1", "1", "2", "EXTENDS", [], 5000)
    assert eid == "2"


def test_edge_reciprocal_claims_rejected_as_cycle(direct_deploy):
    # Stage 11 hardening keeps the claimed ancestry graph structurally acyclic.
    c = direct_deploy(CONTRACT)
    _one_candidate(c)
    _node(c, ahash="na")                             # node "1"
    _node(c, contributor=ADDR_2, ahash="nb")         # node "2"
    e1 = _edge(c, "1", "1", "2", "FORKED_FROM", [], 6000)
    with pytest.raises(Exception):
        _edge(c, "1", "2", "1", "FORKED_FROM", [], 6000)
    with pytest.raises(Exception):
        _edge(c, "1", "2", "1", "DOCUMENTS", [], 4000)
    assert e1 == "1"
    listing = json.loads(c.list_lineage_edges("1", 0, 50))
    assert listing["total"] == 1


def test_edge_rejects_invalid_bps(direct_deploy):
    c = direct_deploy(CONTRACT)
    _one_candidate(c)
    _node(c, ahash="na")
    _node(c, contributor=ADDR_2, ahash="nb")
    with pytest.raises(Exception):
        _edge(c, "1", "1", "2", "FORKED_FROM", [], -1)        # negative
    with pytest.raises(Exception):
        _edge(c, "1", "1", "2", "FORKED_FROM", [], 10001)     # above 10000
    with pytest.raises(Exception):
        _edge(c, "1", "1", "2", "FORKED_FROM", [], True)      # bool != int score
    with pytest.raises(Exception):
        _edge(c, "1", "1", "2", "FORKED_FROM", [], "5000")    # numeric string


def test_edge_rejects_unknown_evidence_ref(direct_deploy):
    c = direct_deploy(CONTRACT)
    _one_candidate(c)
    _evidence(c, "1", host="a.example.com", h="e1")  # evidence "1"
    _node(c, ahash="na")
    _node(c, contributor=ADDR_2, ahash="nb")
    with pytest.raises(Exception):
        _edge(c, "1", "1", "2", "FORKED_FROM", ["1", "999"], 5000)


def test_edge_rejects_evidence_ref_from_another_candidate(direct_deploy):
    c = direct_deploy(CONTRACT)
    _policies(c)
    _reg(c)                                          # candidate "1"
    _reg(c, name="cand2", url="https://example.com/artifact2")  # candidate "2"
    _evidence(c, "2", host="a.example.com", h="e1")  # evidence "1" -> candidate "2"
    _node(c, cid="1", ahash="na")                    # node "1"
    _node(c, cid="1", contributor=ADDR_2, ahash="nb")  # node "2"
    with pytest.raises(Exception):
        # evidence "1" belongs to candidate "2", not the edge's candidate "1"
        _edge(c, "1", "1", "2", "FORKED_FROM", ["1"], 5000)


def test_edge_rejects_duplicate_evidence_refs(direct_deploy):
    c = direct_deploy(CONTRACT)
    _one_candidate(c)
    _evidence(c, "1", host="a.example.com", h="e1")  # evidence "1"
    _node(c, ahash="na")
    _node(c, contributor=ADDR_2, ahash="nb")
    with pytest.raises(Exception):
        _edge(c, "1", "1", "2", "FORKED_FROM", ["1", "1"], 5000)


def test_edge_pagination_bounds(direct_deploy):
    c = direct_deploy(CONTRACT)
    _one_candidate(c)
    _node(c, ahash="na")                             # node "1"
    _node(c, contributor=ADDR_2, ahash="nb")         # node "2"
    _edge(c, "1", "1", "2", "FORKED_FROM", [], 1000)  # edge "1"
    _edge(c, "1", "1", "2", "EXTENDS", [], 2000)      # edge "2"
    _edge(c, "1", "1", "2", "DERIVED_FROM", [], 3000)  # edge "3"

    full = json.loads(c.list_lineage_edges("1", 0, 999))
    assert full["total"] == 3
    assert len(full["items"]) == 3

    page = json.loads(c.list_lineage_edges("1", 1, 1))
    assert [e["edge_id"] for e in page["items"]] == ["2"]

    beyond = json.loads(c.list_lineage_edges("1", 99, 10))
    assert beyond == {"items": [], "total": 3}


# ==========================================================================
# Views — missing lookups + unknown candidate
# ==========================================================================
def test_views_reject_unknown_ids(direct_deploy):
    c = direct_deploy(CONTRACT)
    _one_candidate(c)
    with pytest.raises(Exception):
        c.get_contribution_node("1")                 # none registered yet
    with pytest.raises(Exception):
        c.get_lineage_edge("1")
    with pytest.raises(Exception):
        c.list_contribution_nodes("999", 0, 50)      # unknown candidate
    with pytest.raises(Exception):
        c.list_lineage_edges("999", 0, 50)


def test_empty_listings_for_candidate_without_claims(direct_deploy):
    c = direct_deploy(CONTRACT)
    _one_candidate(c)
    assert json.loads(c.list_contribution_nodes("1", 0, 50)) == {"items": [], "total": 0}
    assert json.loads(c.list_lineage_edges("1", 0, 50)) == {"items": [], "total": 0}


# ==========================================================================
# Pause gating
# ==========================================================================
def test_pause_blocks_node_and_edge_registration(direct_deploy):
    c = direct_deploy(CONTRACT)
    _one_candidate(c)
    _node(c, ahash="na")                             # node "1"
    _node(c, contributor=ADDR_2, ahash="nb")         # node "2"

    c.pause()
    with pytest.raises(Exception):
        _node(c, url="https://repo.example.com/paused", ahash="hp")
    with pytest.raises(Exception):
        _edge(c, "1", "1", "2", "FORKED_FROM", [], 5000)
    # views still work while paused
    assert json.loads(c.list_contribution_nodes("1", 0, 50))["total"] == 2

    c.unpause()
    assert _edge(c, "1", "1", "2", "FORKED_FROM", [], 5000) == "1"


# ==========================================================================
# Candidate lifecycle is NEVER changed by recording lineage claims
# ==========================================================================
def test_lifecycle_unchanged_by_claims_discovered(direct_deploy):
    # Registering nodes/edges on a DISCOVERED candidate leaves it DISCOVERED.
    c = direct_deploy(CONTRACT)
    _one_candidate(c)
    assert json.loads(c.get_candidate("1"))["status"] == "DISCOVERED"
    _node(c, ahash="na")
    _node(c, contributor=ADDR_2, ahash="nb")
    _edge(c, "1", "1", "2", "FORKED_FROM", [], 7000)
    assert json.loads(c.get_candidate("1"))["status"] == "DISCOVERED"


def test_lifecycle_unchanged_by_claims_watching(direct_deploy, direct_vm):
    # A candidate that reached WATCHING in Stage 4 stays WATCHING; recording
    # lineage claims must never promote it to EMERGING/MATERIAL/SYSTEMIC.
    c = direct_deploy(CONTRACT)
    _watching_candidate(c, direct_vm)                # candidate "1" -> WATCHING, ev "1","2"

    _node(c, ahash="na")                             # node "1"
    _node(c, contributor=ADDR_2, ahash="nb")         # node "2"
    _edge(c, "1", "1", "2", "FORKED_FROM", ["1", "2"], 9000)

    cand = json.loads(c.get_candidate("1"))
    assert cand["status"] == "WATCHING"              # unchanged
    # the WATCHING-era latent assessment id is still intact
    assert cand["latent_assessment_id"] == "1"
    assert json.loads(c.list_contribution_nodes("1", 0, 50))["total"] == 2
    assert json.loads(c.list_lineage_edges("1", 0, 50))["total"] == 1


# ==========================================================================
# Vocabulary + bounds introspection (additive)
# ==========================================================================
def test_stage5_vocabulary_and_bounds_exposed(direct_deploy):
    c = direct_deploy(CONTRACT)
    info = json.loads(c.get_protocol_info())
    vocab = info["vocabulary"]
    assert len(vocab["contribution_artifact_types"]) == 10
    assert "SOURCE_CODE" in vocab["contribution_artifact_types"]
    assert "OTHER" in vocab["contribution_artifact_types"]
    assert len(vocab["contribution_roles"]) == 10
    assert "ORIGINAL_AUTHOR" in vocab["contribution_roles"]
    assert vocab["contribution_node_statuses"] == ["CLAIMED"]
    assert vocab["lineage_edge_statuses"] == ["CLAIMED"]
    # the relationship allowlist (declared in Stage 1) has all ten relationships
    assert len(vocab["lineage_relationships"]) == 10
    assert "FORKED_FROM" in vocab["lineage_relationships"]
    assert "INSPIRES" in vocab["lineage_relationships"]
    assert info["bounds"]["max_artifact_hash_len"] == 128
