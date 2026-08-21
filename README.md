# SEEDLING

> A reusable latent-public-goods discovery, lineage-attribution, and progressive retroactive-funding primitive on GenLayer.

**Pattern:** `OBSCURE CONTRIBUTION → LATENT VALUE → LONGITUDINAL EVIDENCE → PUBLIC VALUE → LINEAGE ATTRIBUTION → PROGRESSIVE RPGF`

SEEDLING discovers obscure public contributions early, tracks whether they become real infrastructure, reconstructs who made that value possible, and progressively unlocks retroactive funding as public importance emerges. It separates two questions that must never be collapsed: **latent significance** (does this show credible evidence of becoming valuable infrastructure?) and **realized public value** (did reality later confirm it?). Popularity is never treated as public value.

## Architecture

Frontend + GenLayer Intelligent Contract only. **No backend, no private database, no hidden ranking service.** All canonical state lives on-chain.

- **Contract** — Python `gl.Contract` (`contracts/seedling.py`)
- **Frontend** — React/Vite client calling the contract directly through `genlayer-js`.
- **Deployment** — owner-controlled canonical StudioNet contract at
  `0x9f4675FfA027eBB82Bb60182F40FDBAB7038F766` (chain 61999).

## Production

- Frontend: https://seedling-lovat.vercel.app
- Source: https://github.com/Chinny070/seedling
- Canonical contract: `0x9f4675FfA027eBB82Bb60182F40FDBAB7038F766`

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
- `tests/direct/test_stage12.py` — complete in-process lifecycle and deployment-readiness integration scenarios.

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
11. **Storage bounding, protocol hardening, and release-safety audit** ✅
12. **Final contract integration audit + deployment readiness** ✅
13. Frontend GenLayer integration foundation ✅
14. **Canonical StudioNet deployment + live frontend binding** ✅ *current*
15. Integration Hub + guided demo + reusability audit + docs
16. GitHub/Vercel release + Portal submission readiness

The repository stays functional after every stage.

## Protocol lifecycle

Candidates enter as `DISCOVERED`, bind immutable policy-version IDs, collect and
freeze compact latent evidence, and receive a comparative GenLayer latent assessment.
A successful assessment moves the candidate to `WATCHING`. Repeated frozen impact
checkpoints then adjudicate realized public value and evidence-based contributor
lineage. Deterministic funding accounting unlocks only the incremental amount up to
the bound policy tier cap. Appeals can uphold, modify, or void an effective result
without rewriting the original verdict, and checkpoint finalization is irreversible.

GenLayer remains essential where evidence requires substantive interpretation:
independent reuse, uniqueness, substitutes, adoption quality, anti-gaming risk,
realized importance, causal lineage, and appeals. Each flow uses a frozen on-chain
package, bounded rendering of stored public URLs, explicit criteria, comparative
validator reasoning, exact-schema validation, and storage only after success.

The frozen constructor and all 56 public methods, parameter types, return types,
frontend read routes, lifecycle values, and expected errors are documented in
[`docs/CONTRACT_INTERFACE.md`](docs/CONTRACT_INTERFACE.md).

The Stage 13 direct-contract frontend lives in [`frontend/`](frontend/). Its
configuration, StudioNet wallet flow, transaction-finality model, routes, local
commands, production build, and security boundaries are documented in
[`frontend/README.md`](frontend/README.md). A real
`VITE_SEEDLING_CONTRACT_ADDRESS` is required; no placeholder is treated as a live
deployment and no demo data is mixed with contract reads.

Canonical and verification deployment provenance, the audited deployment package,
and the remaining manual checks are documented in
[`docs/STUDIONET_DEPLOYMENT.md`](docs/STUDIONET_DEPLOYMENT.md).

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
