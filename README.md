# SEEDLING

> A reusable latent-public-goods discovery, lineage-attribution, and progressive retroactive-funding primitive on GenLayer.

**Pattern:** `OBSCURE CONTRIBUTION → LATENT VALUE → LONGITUDINAL EVIDENCE → PUBLIC VALUE → LINEAGE ATTRIBUTION → PROGRESSIVE RPGF`

SEEDLING discovers obscure public contributions early, tracks whether they become real infrastructure, reconstructs who made that value possible, and progressively unlocks retroactive funding as public importance emerges. It separates two questions that must never be collapsed: **latent significance** (does this show credible evidence of becoming valuable infrastructure?) and **realized public value** (did reality later confirm it?). Popularity is never treated as public value.

## Architecture

Frontend + GenLayer Intelligent Contract only. **No backend, no private database, no hidden ranking service.** All canonical state lives on-chain.

- **Contract** — Python `gl.Contract` (`contracts/seedling.py`)
- **Frontend** — React + TypeScript + Vite + `genlayer-js` (added Stage 13–14)
- **Network** — GenLayer StudioNet (chain id `61999`, RPC `https://studio.genlayer.com/api`; chain derived from `genlayer-js/chains` `studionet`)

GenLayer adjudicates the non-deterministic questions (latent significance, independent reuse, uniqueness, substitutes, realized public value, replacement difficulty, anti-gaming, lineage, contributor attribution, appeals). Deterministic contract logic owns all arithmetic — funding caps, cumulative release, contributor allocation, and policy gates. **No LLM arithmetic, no double release.**

## Verified GenLayer API surface

Confirmed against installed tooling (`gltest 0.29.2`, `genlayer-py 0.16.3`) and two deployed sibling contracts — not guessed.

- Contract: `from genlayer import *`; `class X(gl.Contract)`; storage `u256` / `TreeMap[str, str]` / `Address`; `@gl.public.write[.payable]`, `@gl.public.view`; `gl.message.sender_address.as_hex`, `gl.message.value`; `gl.vm.UserError(...)`.
- Adjudication: `gl.eq_principle.prompt_comparative(fn, criteria)` wrapping `gl.nondet.exec_prompt(...)` + `gl.nondet.web.render(url, mode="text")`.
- Header pragma: `# v0.2.16` + `# { "Depends": "py-genlayer:..." }`.

## Development

Requires Python ≥ 3.12 and `genlayer-test` (`gltest`).

```bash
pytest tests/ -v
```

- `tests/direct/` — in-process GenVM execution, no node required (deterministic logic, status machines, funding math).
- `tests/integration/` — runs against a GenLayer Studio/simulator endpoint (added Stage 11–12).

## Build roadmap (16 stages)

1. **Repo inspection, API verification, storage scaffolding, test foundation** ✅
2. Candidate lifecycle + ObservationPolicy + FundingPolicy ✅
3. Candidate evidence + latent-evidence freeze ✅
4. **Latent-value adjudication** ✅
5. Contribution nodes + lineage edges ✅
6. **Impact checkpoint lifecycle + checkpoint evidence** ✅
7. **Public-value adjudication + anti-gaming + substitute analysis** ✅
8. **Lineage adjudication + contributor attribution** ✅
9. **Deterministic progressive funding preview** ✅
10. **Appeals + checkpoint finalization** ✅
11. **Storage bounding, protocol hardening, and release-safety audit** ✅ *current*
12. Manual Studio deployment + schema verification
13. Frontend GenLayer integration foundation
14. Full product frontend
15. Integration Hub + guided demo + reusability audit + docs
16. GitHub/Vercel release + Portal submission readiness

The repository stays functional after every stage.

## Storage economics and historical integrity

SEEDLING stores compact canonical protocol records on-chain: candidates, immutable
policy versions, URL/hash evidence references, frozen evidence-ID snapshots,
adjudication results, contribution claims, funding calculations, appeals, and
checkpoint finalization references. It does not store fetched page bodies, model
context, files, token-transfer state, or a private off-chain database.

Every user-controlled string and per-candidate collection is bounded. Evidence,
checkpoints, contribution nodes, lineage edges, appeals, and policy-family versions
have deterministic limits. Public list methods clamp pages to 50 records with stable
creation-order pagination; legacy whole-family policy-history views are safe because
each family is capped at 32 immutable versions. Global registries remain append-only
and are read only through bounded pages, preserving protocol utility without building
unbounded responses.

Frozen evidence snapshots retain IDs and compact diversity metadata rather than
duplicating evidence bodies. Historical policy IDs remain bound to candidates and
checkpoints, so later policy versions cannot reprice finalized history. Impact,
lineage, funding, and appeal records are append-only; effective appeal modifications
are stored separately from original verdicts. Finalized or voided checkpoints reject
replay, funding is capped and monotonic, and the claimed lineage graph rejects
self-loops, duplicates, and directed cycles. Owner authority remains limited to the
global pause switch; it cannot rewrite evidence, adjudication, lineage, funding, or
appeal history.
