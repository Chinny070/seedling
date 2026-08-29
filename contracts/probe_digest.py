# v0.2.16
# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

# DIGEST PROBE - throwaway operator tool, NOT part of the SEEDLING protocol.
#
# Purpose: answer one question before evidence is ever submitted -- "what
# content_hash will SEEDLING compute for this URL?" -- so an operator never
# freezes an evidence set around a digest that adjudication will later reject.
#
# The digest SEEDLING verifies is taken from gl.nondet.web.render(url,
# mode="text") as executed inside GenVM. That exact string cannot be reproduced
# off-chain: it depends on the renderer's own text extraction, not on the raw
# bytes a normal HTTP client downloads. So the only trustworthy way to learn the
# digest is to render the URL through the same runtime and hash it there, which
# is all this contract does.
#
# _render_digest below MUST stay byte-identical to _render_digest in
# contracts/seedling.py and render_digest in tests/direct/_archive.py. If those
# three ever disagree, this probe stops predicting anything and becomes actively
# misleading.
#
# Deliberately minimal: no owner, no pause, no access control, no validation of
# the url beyond what the renderer itself enforces. It stores nothing that
# matters and is safe to abandon after use. Do NOT extend it into protocol
# infrastructure -- SEEDLING must never depend on a probe deployment.

from genlayer import *

import hashlib
import json


def _render_digest(text: str) -> str:
    """Canonical digest of the exact text representation used during adjudication.

    Byte-identical to contracts/seedling.py::_render_digest. Procedure, in order:
      1. CRLF and lone CR both become LF
      2. trailing spaces and tabs are stripped from every line
      3. leading and trailing blank lines are dropped
      4. encode UTF-8, SHA-256, lowercase hex, "sha256:" prefix
    """
    unified = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = []
    for line in unified.split("\n"):
        lines.append(line.rstrip(" \t"))
    normalized = "\n".join(lines).strip("\n")
    return "sha256:" + hashlib.sha256(normalized.encode("utf-8")).hexdigest()


class DigestProbe(gl.Contract):
    # Last probe result, kept only so the digest can be read back without
    # re-rendering (and re-paying for) the same page.
    last: TreeMap[str, str]

    def __init__(self):
        pass

    @gl.public.write
    def probe(self, url: str) -> str:
        """Render `url` and return the digest SEEDLING will expect for it.

        Runs under strict equality: every validator renders the page
        independently and the transaction only lands if they all derive the
        same digest. A page that fails to agree is exactly the page that would
        have failed SEEDLING adjudication later -- so disagreement here is a
        useful result, not a malfunction. Unstable pages (ads, timestamps,
        per-request tokens) are what raw `id_` archive snapshots avoid.
        """
        def render_and_digest():
            page = gl.nondet.web.render(url, mode="text")
            if not isinstance(page, str):
                raise gl.vm.UserError("EXPECTED: url did not render as text")
            return _render_digest(page)

        digest = gl.eq_principle.strict_eq(render_and_digest)
        self.last[url] = digest
        return digest

    @gl.public.write
    def probe_preview(self, url: str, chars: int) -> str:
        """Return the digest plus the leading `chars` of rendered text.

        For diagnosing a mismatch: seeing what the renderer actually produced
        (navigation chrome, an archive banner, an error page served with a 200)
        usually explains it immediately. Bounded so a large page cannot blow up
        the return value.
        """
        if chars < 1 or chars > 4000:
            raise gl.vm.UserError("EXPECTED: chars must be 1-4000")

        def render_and_report():
            page = gl.nondet.web.render(url, mode="text")
            if not isinstance(page, str):
                raise gl.vm.UserError("EXPECTED: url did not render as text")
            return json.dumps({
                "digest": _render_digest(page),
                "rendered_chars": len(page),
                "head": page[:chars],
            })

        result = gl.eq_principle.strict_eq(render_and_report)
        self.last[url] = json.loads(result)["digest"]
        return result

    @gl.public.view
    def get_last(self, url: str) -> str:
        """Read back a digest already probed, without rendering again."""
        if url not in self.last:
            raise gl.vm.UserError("EXPECTED: url has not been probed")
        return self.last[url]
