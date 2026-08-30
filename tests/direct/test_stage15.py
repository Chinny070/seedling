"""Stage 15 tests - preview_evidence_digest, the submission aid.

The digest a submitter must supply comes from text only the contract can
render. These tests pin the two properties that make the preview trustworthy:
it reports exactly the digest the adjudication paths verify against, and it
enforces the same archive-source rule as submission, so a preview can never
bless a url that evidence submission would reject.
"""

import json
import pytest

from tests.direct._archive import wb, render_digest

CONTRACT = "contracts/seedling.py"

BODY = "Line one.\r\nLine two.   \n\nLine four.\n"
URL = wb("https://example.org/readme")


def test_preview_reports_the_digest_adjudication_will_expect(direct_deploy, direct_vm):
    c = direct_deploy(CONTRACT)
    direct_vm.mock_web(r"example\.org", {"body": BODY})
    report = json.loads(c.preview_evidence_digest(URL))
    assert report["digest"] == render_digest(BODY)
    assert report["rendered_chars"] == len(BODY)
    assert report["head"] == BODY[:800]


def test_preview_rejects_urls_evidence_submission_would_reject(direct_deploy, direct_vm):
    # A preview that accepted non-archive urls would hand back a digest for a
    # url the submitter could never actually use.
    c = direct_deploy(CONTRACT)
    direct_vm.mock_web(r"example\.org", {"body": BODY})
    for bad in (
        "https://example.org/readme",                       # not archived
        "https://web.archive.org/web/20240101000000/https://example.org/x",  # no id_
        "not-a-url",
    ):
        with pytest.raises(Exception):
            c.preview_evidence_digest(bad)


def test_preview_writes_no_protocol_state(direct_deploy, direct_vm):
    c = direct_deploy(CONTRACT)
    direct_vm.mock_web(r"example\.org", {"body": BODY})
    before = json.loads(c.get_protocol_info())["counts"]
    c.preview_evidence_digest(URL)
    assert json.loads(c.get_protocol_info())["counts"] == before


def test_preview_fails_when_the_url_cannot_be_rendered(direct_deploy):
    c = direct_deploy(CONTRACT)
    with pytest.raises(Exception):
        c.preview_evidence_digest(URL)
