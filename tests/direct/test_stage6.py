"""Stage 6 direct tests — impact checkpoints and checkpoint evidence freeze.

Only Stage 4's nondeterministic boundaries are mocked to prepare WATCHING
candidates. Stage 6 itself performs no nondeterministic calls.
"""

import json

import pytest


from tests.direct._archive import wb, render_digest, EVIDENCE_BODY, EVIDENCE_DIGEST

CONTRACT = "contracts/seedling.py"
LLM_MATCH = "adjudicator for SEEDLING"
CP_START = 1600002000
CP_END = 1600012000


def _verdict(evidence_ids):
    return {
        "latent_value_bps": 6200,
        "independent_reuse_bps": 5800,
        "uniqueness_bps": 7000,
        "substitution_risk_bps": 3000,
        "maintainer_health_bps": 6500,
        "ecosystem_positioning_bps": 6000,
        "gaming_risk_bps": 1500,
        "reason_codes": ["EARLY_INDEPENDENT_REUSE"],
        "evidence_refs": evidence_ids,
        "summary": "Credible early reuse with bounded gaming risk.",
    }


def _policies(c, min_cat=1, min_src=1):
    c.create_observation_policy(
        "obs", ["OPEN_SOURCE_LIBRARY"], min_cat, min_src,
        "latent rules", "impact rules", "lineage rules",
        "gaming rules", "substitute rules", 86400,
    )
    c.create_funding_policy(
        "fund", 100, 500, 1500, 4000, 9000, 2000, 3000, 6000,
    )


def _watching_candidate(
    c,
    vm,
    name="cand",
    artifact_url=wb("https://artifact.example.com/cand"),
    evidence_url=wb("https://latent.example.com/cand"),
    evidence_hash=EVIDENCE_DIGEST,
    min_cat=1,
    min_src=1,
):
    cid = c.register_candidate(
        name, "candidate description", "OPEN_SOURCE_LIBRARY", artifact_url,
        "2020-01-01", True, "1", "1",
    )
    categories = ["SOURCE_REPOSITORY", "PACKAGE_REGISTRY"]
    evidence_ids = []
    required = max(min_cat, min_src)
    for i in range(required):
        url = evidence_url if i == 0 else wb(f"https://latent{i}.{name}.example.com/e")
        # every mocked source renders the same body, so one digest binds them all
        content_hash = evidence_hash
        evidence_ids.append(c.submit_candidate_evidence(
            cid, categories[i % len(categories)], url, content_hash,
            "latent source evidence", 1600000000, 1600001000,
        ))
    assert c.freeze_latent_evidence(cid) == "LATENT"
    vm.clear_mocks()
    vm.mock_web(r"example\.com", {"body": EVIDENCE_BODY})
    vm.mock_llm(
        LLM_MATCH,
        "```json\n" + json.dumps(_verdict(evidence_ids)) + "\n```",
    )
    json.loads(c.evaluate_latent_value(cid))
    assert json.loads(c.get_candidate(cid))["status"] == "WATCHING"
    return cid, evidence_ids[0]


def _setup(c, vm, min_cat=1, min_src=1):
    _policies(c, min_cat, min_src)
    return _watching_candidate(c, vm, min_cat=min_cat, min_src=min_src)


def _open(c, cid="1", start=CP_START, end=CP_END):
    return c.open_checkpoint(cid, start, end)


def _submit(
    c,
    checkpoint_id="1",
    source_type="SOURCE_REPOSITORY",
    url=wb("https://impact.example.com/one"),
    content_hash=EVIDENCE_DIGEST,
    summary="checkpoint evidence",
    start=CP_START,
    end=CP_START + 100,
):
    return c.submit_checkpoint_evidence(
        checkpoint_id, source_type, url, content_hash, summary, start, end,
    )


def test_open_checkpoint_success_and_schema(direct_deploy, direct_vm):
    c = direct_deploy(CONTRACT)
    _setup(c, direct_vm)
    assert _open(c) == "1"
    rec = json.loads(c.get_checkpoint("1"))
    assert set(rec) == {
        "checkpoint_id", "candidate_id", "period_start", "period_end",
        "status", "evidence_count", "impact_verdict_id",
        "lineage_verdict_id", "appeal_id", "created_at",
    }
    assert rec["status"] == "OPEN"
    assert rec["evidence_count"] == 0
    assert rec["impact_verdict_id"] == rec["lineage_verdict_id"] == rec["appeal_id"] == ""


def test_open_requires_existing_and_watching_candidate(direct_deploy, direct_vm):
    c = direct_deploy(CONTRACT)
    with pytest.raises(Exception):
        _open(c, "999")
    _policies(c)
    cid = c.register_candidate(
        "new", "desc", "OPEN_SOURCE_LIBRARY", wb("https://example.com/new"),
        "2020-01-01", True, "1", "1",
    )
    with pytest.raises(Exception):
        _open(c, cid)
    c.submit_candidate_evidence(
        cid, "SOURCE_REPOSITORY", wb("https://example.com/e"), EVIDENCE_DIGEST, "summary",
        1600000000, 1600001000,
    )
    c.freeze_latent_evidence(cid)
    with pytest.raises(Exception):
        _open(c, cid)


@pytest.mark.parametrize("start,end", [
    (CP_START, CP_START),
    (CP_START + 1, CP_START),
    (-1, CP_END),
    (CP_START, 4102444800),
    (True, CP_END),
])
def test_open_rejects_invalid_period(direct_deploy, direct_vm, start, end):
    c = direct_deploy(CONTRACT)
    _setup(c, direct_vm)
    with pytest.raises(Exception):
        _open(c, start=start, end=end)


def test_duplicate_active_checkpoint_rejected(direct_deploy, direct_vm):
    c = direct_deploy(CONTRACT)
    _setup(c, direct_vm)
    _open(c)
    with pytest.raises(Exception):
        c.open_checkpoint("1", CP_END, CP_END + 1000)


def test_checkpoint_ids_are_global_monotonic(direct_deploy, direct_vm):
    c = direct_deploy(CONTRACT)
    _policies(c)
    cid1, _ = _watching_candidate(c, direct_vm)
    cid2, _ = _watching_candidate(
        c, direct_vm, "cand2", wb("https://artifact.example.com/two"),
        wb("https://latent.example.com/two"), EVIDENCE_DIGEST,
    )
    assert c.open_checkpoint(cid1, CP_START, CP_END) == "1"
    assert c.open_checkpoint(cid2, CP_START, CP_END) == "2"


def test_only_candidate_submitter_may_open(direct_deploy, direct_vm, direct_alice):
    c = direct_deploy(CONTRACT)
    _setup(c, direct_vm)
    direct_vm.sender = direct_alice
    with pytest.raises(Exception):
        _open(c)


def test_submit_checkpoint_evidence_success(direct_deploy, direct_vm):
    c = direct_deploy(CONTRACT)
    _, latent_eid = _setup(c, direct_vm)
    _open(c)
    eid = _submit(c)
    assert eid != latent_eid
    rec = json.loads(c.get_evidence(eid))
    assert rec["candidate_id"] == "1"
    assert rec["checkpoint_id"] == "1"
    assert rec["status"] == "SUBMITTED"
    assert rec["source_host"] == "impact.example.com"
    assert json.loads(c.get_checkpoint("1"))["evidence_count"] == 1


def test_submit_requires_existing_open_checkpoint(direct_deploy, direct_vm):
    c = direct_deploy(CONTRACT)
    _setup(c, direct_vm)
    with pytest.raises(Exception):
        _submit(c, "999")
    _open(c)
    _submit(c)
    c.freeze_checkpoint("1")
    with pytest.raises(Exception):
        _submit(c, "1", content_hash=EVIDENCE_DIGEST)


def test_submit_rejects_invalid_type_and_url(direct_deploy, direct_vm):
    c = direct_deploy(CONTRACT)
    _setup(c, direct_vm)
    _open(c)
    with pytest.raises(Exception):
        _submit(c, source_type="UNKNOWN")
    for url in ("ftp://example.com/x", "example.com/x", "https://localhost/x"):
        with pytest.raises(Exception):
            _submit(c, url=url)


def test_hostname_normalization_and_ports_collapse(direct_deploy, direct_vm):
    c = direct_deploy(CONTRACT)
    _setup(c, direct_vm, min_cat=1, min_src=2)
    _open(c)
    e1 = _submit(c, url=wb("https://User@EXAMPLE.com:80/a"), content_hash=EVIDENCE_DIGEST)
    e2 = _submit(c, url=wb("https://example.com:8080/b"), content_hash=EVIDENCE_DIGEST)
    assert json.loads(c.get_evidence(e1))["source_host"] == "example.com"
    assert json.loads(c.get_evidence(e2))["source_host"] == "example.com"
    live = json.loads(c.get_checkpoint_evidence_set("1"))
    assert live["distinct_host_count"] == 1
    with pytest.raises(Exception):
        c.freeze_checkpoint("1")


def test_missing_content_hash_and_oversized_summary_rejected(direct_deploy, direct_vm):
    c = direct_deploy(CONTRACT)
    _setup(c, direct_vm)
    _open(c)
    for value in ("", "has whitespace", "x" * 129):
        with pytest.raises(Exception):
            _submit(c, content_hash=value)
    with pytest.raises(Exception):
        _submit(c, summary="x" * 1001)


def test_checkpoint_duplicate_is_scoped_and_latent_source_reuse_allowed(
    direct_deploy, direct_vm,
):
    c = direct_deploy(CONTRACT)
    _policies(c)
    _, _ = _watching_candidate(
        c, direct_vm, evidence_url=wb("https://same.example.com/source"),
        evidence_hash=EVIDENCE_DIGEST,
    )
    _open(c)
    assert _submit(
        c, url=wb("https://same.example.com/source"), content_hash=EVIDENCE_DIGEST,
    ) == "2"
    with pytest.raises(Exception):
        _submit(c, url=wb("https://same.example.com/source"), content_hash=EVIDENCE_DIGEST)
    with pytest.raises(Exception):
        _submit(c, url=wb("https://SAME.example.com/source/"), content_hash=EVIDENCE_DIGEST)


@pytest.mark.parametrize("start,end", [
    (CP_START + 10, CP_START),
    (-1, CP_START),
    (CP_START - 1, CP_START),
    (CP_START, CP_END + 1),
    (CP_START, 4102444800),
])
def test_checkpoint_evidence_period_validation(direct_deploy, direct_vm, start, end):
    c = direct_deploy(CONTRACT)
    _setup(c, direct_vm)
    _open(c)
    with pytest.raises(Exception):
        _submit(c, start=start, end=end)


def test_checkpoint_evidence_cap(direct_deploy, direct_vm):
    c = direct_deploy(CONTRACT)
    _setup(c, direct_vm)
    _open(c)
    for i in range(64):
        _submit(
            c,
            url=wb(f"https://h{i}.example.com/e"),
            content_hash=EVIDENCE_DIGEST,
        )
    with pytest.raises(Exception):
        _submit(c, url=wb("https://overflow.example.com/e"), content_hash=EVIDENCE_DIGEST)
    assert json.loads(c.list_checkpoint_evidence("1", 0, 100))["total"] == 64


def test_freeze_requires_evidence(direct_deploy, direct_vm):
    c = direct_deploy(CONTRACT)
    _setup(c, direct_vm)
    _open(c)
    with pytest.raises(Exception):
        c.freeze_checkpoint("1")


def test_freeze_enforces_categories(direct_deploy, direct_vm):
    c = direct_deploy(CONTRACT)
    _setup(c, direct_vm, min_cat=2, min_src=1)
    _open(c)
    _submit(c, url=wb("https://a.example.com/a"), content_hash=EVIDENCE_DIGEST)
    _submit(c, url=wb("https://b.example.com/b"), content_hash=EVIDENCE_DIGEST)
    with pytest.raises(Exception):
        c.freeze_checkpoint("1")


def test_freeze_enforces_distinct_hosts(direct_deploy, direct_vm):
    c = direct_deploy(CONTRACT)
    _setup(c, direct_vm, min_cat=1, min_src=2)
    _open(c)
    _submit(c, url=wb("https://same.example.com/a"), content_hash=EVIDENCE_DIGEST)
    _submit(c, url=wb("https://same.example.com/b"), content_hash=EVIDENCE_DIGEST)
    with pytest.raises(Exception):
        c.freeze_checkpoint("1")


def test_successful_freeze_snapshot_and_lifecycle(direct_deploy, direct_vm):
    c = direct_deploy(CONTRACT)
    _setup(c, direct_vm, min_cat=2, min_src=2)
    _open(c)
    e1 = _submit(c, url=wb("https://a.example.com/a"), content_hash=EVIDENCE_DIGEST)
    e2 = _submit(
        c, source_type="PACKAGE_REGISTRY", url=wb("https://b.example.com/b"),
        content_hash=EVIDENCE_DIGEST,
    )
    assert c.freeze_checkpoint("1") == "EVIDENCE_FROZEN"
    cp = json.loads(c.get_checkpoint("1"))
    snap = json.loads(c.get_checkpoint_evidence_set("1"))
    assert cp["status"] == "EVIDENCE_FROZEN"
    assert snap["evidence_ids"] == [e1, e2]
    assert snap["evidence_count"] == 2
    assert snap["observation_policy_id"] == "1"
    assert snap["funding_policy_id"] == "1"
    assert snap["latent_assessment_id"] == "1"
    assert snap["requirements_met"] is True
    assert json.loads(c.get_candidate("1"))["status"] == "WATCHING"
    assert all(
        item["status"] == "FROZEN"
        for item in json.loads(c.list_checkpoint_evidence("1", 0, 10))["items"]
    )


def test_frozen_snapshot_is_immutable_and_double_freeze_rejected(direct_deploy, direct_vm):
    c = direct_deploy(CONTRACT)
    _setup(c, direct_vm)
    _open(c)
    eid = _submit(c)
    before = json.loads(c.get_evidence(eid))
    c.freeze_checkpoint("1")
    snap1 = json.loads(c.get_checkpoint_evidence_set("1"))
    with pytest.raises(Exception):
        _submit(c, content_hash=EVIDENCE_DIGEST)
    with pytest.raises(Exception):
        c.freeze_checkpoint("1")
    snap2 = json.loads(c.get_checkpoint_evidence_set("1"))
    after = json.loads(c.get_evidence(eid))
    assert snap1 == snap2
    assert before["content_hash"] == after["content_hash"]
    assert after["status"] == "FROZEN"


def test_inactive_bound_policy_still_freezes(direct_deploy, direct_vm):
    c = direct_deploy(CONTRACT)
    _setup(c, direct_vm)
    c.set_observation_policy_status("1", False)
    _open(c)
    _submit(c)
    assert c.freeze_checkpoint("1") == "EVIDENCE_FROZEN"


def test_checkpoint_pagination_is_bounded(direct_deploy, direct_vm):
    c = direct_deploy(CONTRACT)
    _setup(c, direct_vm)
    _open(c)
    for i in range(55):
        _submit(c, url=wb(f"https://p{i}.example.com/e"), content_hash=EVIDENCE_DIGEST)
    page = json.loads(c.list_checkpoint_evidence("1", -5, 999))
    assert page["total"] == 55
    assert len(page["items"]) == 50
    checkpoints = json.loads(c.list_checkpoints("1", -1, 999))
    assert checkpoints["total"] == 1
    assert len(checkpoints["items"]) == 1


def test_pause_blocks_open_submit_and_freeze(direct_deploy, direct_vm):
    c = direct_deploy(CONTRACT)
    _setup(c, direct_vm)
    c.pause()
    with pytest.raises(Exception):
        _open(c)
    c.unpause()
    _open(c)
    c.pause()
    with pytest.raises(Exception):
        _submit(c)
    c.unpause()
    _submit(c)
    c.pause()
    with pytest.raises(Exception):
        c.freeze_checkpoint("1")


def test_stage6_protocol_vocabulary_and_method_count(direct_deploy):
    c = direct_deploy(CONTRACT)
    info = json.loads(c.get_protocol_info())
    assert info["vocabulary"]["checkpoint_allowed_candidate_statuses"] == [
        "WATCHING", "EMERGING", "MATERIAL", "SYSTEMIC",
    ]
    assert info["bounds"]["max_evidence_per_checkpoint"] == 64
    assert info["conventions"]["checkpoint_periods"] == "unix_timestamp_integers"
    assert info["conventions"]["one_active_checkpoint_per_candidate"] is True
