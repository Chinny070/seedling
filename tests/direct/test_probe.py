"""Probe smoke tests — contracts/probe_digest.py.

The probe is an operator tool, not protocol code, so these tests only establish
the two things an operator has to be able to trust:

  * it loads and runs under real GenVM (so a Studio deployment will not fail
    on an unavailable API), and
  * the digest it reports is the SAME digest SEEDLING computes for the same
    rendered text.

The renderer is mocked here exactly as it is everywhere else in this suite, so
these tests cannot prove anything about real Wayback pages. That is the whole
reason the probe exists: only a live deployment can answer that.
"""

import json
import pytest

from tests.direct._archive import render_digest

CONTRACT = "contracts/probe_digest.py"

PAGE = "Public README.\r\nReused by unrelated projects.   \n\n"


def test_probe_reports_the_digest_seedling_will_expect(direct_deploy, direct_vm):
    c = direct_deploy(CONTRACT)
    direct_vm.mock_web(r"example\.com", {"body": PAGE})
    digest = c.probe("https://example.com/readme")
    # The probe's answer must equal the shared canonical normalization, which is
    # byte-identical to the contract's _render_digest.
    assert digest == render_digest(PAGE)
    assert digest.startswith("sha256:")
    # CRLF, trailing spaces, and trailing blank lines must all normalize away.
    assert digest == render_digest("Public README.\nReused by unrelated projects.")


def test_probed_digest_is_readable_without_rendering_again(direct_deploy, direct_vm):
    c = direct_deploy(CONTRACT)
    direct_vm.mock_web(r"example\.com", {"body": PAGE})
    digest = c.probe("https://example.com/readme")
    assert c.get_last("https://example.com/readme") == digest
    with pytest.raises(Exception):
        c.get_last("https://example.com/never-probed")


def test_preview_returns_bounded_rendered_head(direct_deploy, direct_vm):
    c = direct_deploy(CONTRACT)
    direct_vm.mock_web(r"example\.com", {"body": PAGE})
    report = json.loads(c.probe_preview("https://example.com/readme", 10))
    assert report["digest"] == render_digest(PAGE)
    assert report["rendered_chars"] == len(PAGE)
    assert report["head"] == PAGE[:10]
    for bad in (0, 4001):
        with pytest.raises(Exception):
            c.probe_preview("https://example.com/readme", bad)


def test_unrenderable_url_fails_instead_of_reporting_a_digest(direct_deploy):
    # No web mock at all -> the render raises. The probe must surface that
    # rather than hand back the digest of an error placeholder.
    c = direct_deploy(CONTRACT)
    with pytest.raises(Exception):
        c.probe("https://example.com/readme")
