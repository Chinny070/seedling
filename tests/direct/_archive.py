"""Shared helpers for the archive-source and digest-binding invariants.

`render_digest` MUST stay byte-identical to `_render_digest` in
contracts/seedling.py. It is duplicated here rather than imported because the
contract runs inside GenVM and cannot be imported as a normal Python module —
if one copy changes, the other has to change with it.
"""

import hashlib

# Any fixed, well-formed Wayback snapshot prefix works for tests; only its
# shape matters to the contract, never the timestamp.
ARCHIVE_PREFIX = "https://web.archive.org/web/20240101000000id_/"


def wb(origin_url: str) -> str:
    """Wrap an origin URL as a raw Wayback snapshot URL."""
    return ARCHIVE_PREFIX + origin_url


# One canonical rendered body shared by the web mocks, so every submitted
# content_hash in the suite can be a real digest of what adjudication will
# actually read. Tests that care about *which* url was fetched still mock
# distinct hosts; they just no longer need distinct bodies.
EVIDENCE_BODY = "Public README. Reused by several unrelated, independent projects."


def render_digest(text: str) -> str:
    """Canonical digest of a rendered text representation.

    Mirrors contracts/seedling.py::_render_digest exactly: CRLF/CR -> LF, strip
    trailing spaces and tabs per line, drop leading/trailing blank lines,
    UTF-8, SHA-256, lowercase hex.
    """
    unified = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = []
    for line in unified.split("\n"):
        lines.append(line.rstrip(" \t"))
    normalized = "\n".join(lines).strip("\n")
    return "sha256:" + hashlib.sha256(normalized.encode("utf-8")).hexdigest()


# Digest of EVIDENCE_BODY under the canonical normalization above. Every piece
# of mocked evidence in the suite is submitted with this value.
EVIDENCE_DIGEST = render_digest(EVIDENCE_BODY)
