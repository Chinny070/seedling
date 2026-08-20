# SEEDLING agent handover

Last updated: 2026-08-20  
Repository: https://github.com/Chinny070/seedling  
Production frontend: https://seedling-lovat.vercel.app

This document is the operational handover for another coding agent. Read it in
full before making changes. The repository is already deployed to production;
the current task is maintenance or explicitly requested follow-on work, not a new
deployment.

## 1. Non-negotiable production facts

- Canonical GenLayer contract:
  `0x72C0Ee823D32905f5D0b36a182Cfa526eA2e08aC`
- Network: GenLayer StudioNet
- Chain ID: `61999`
- StudioNet RPC: `https://studio.genlayer.com/api`
- Canonical contract owner:
  `0xaffE15eEc45b68835cc9E5B4Ab85dD5deaE8e70b`
- Production frontend: https://seedling-lovat.vercel.app
- Public GitHub repository: https://github.com/Chinny070/seedling
- Final known Git commit at handover:
  `3fb75f6010d1571f26d73edb54b443681de3cd7c`
- Contract constructor: `Seedling()` with **zero arguments**.
- Contract ABI: 56 public methods: 33 views and 23 writes.
- Audited contract SHA-256:
  `4FB7BB560C445D35C180F62C067624905386431F5BB0311AAC3B19193CBB7873`
- Audited Git blob hash for `contracts/seedling.py`:
  `8af172dc01fac4da64a10dc61c8e659c32fcbf48`

Do not deploy or redeploy the contract, change the canonical address, push code,
or redeploy Vercel unless the user explicitly authorizes that exact action.
Never treat the older verification address as canonical.

Older verification-only address:
`0xcb2FfAC9E22dfE582Ab3A9F45CcA1FAB0cEC1D25`.

## 2. Product purpose

SEEDLING is a reusable GenLayer-native primitive for:

1. discovering obscure public-good candidates;
2. assessing latent infrastructure potential;
3. collecting immutable longitudinal evidence;
4. adjudicating realized public value;
5. recording and adjudicating contribution lineage;
6. calculating deterministic progressive retroactive funding;
7. handling bounded appeals and irreversible checkpoint finalization.

The central product distinction is:

- **Latent significance:** could an obscure contribution become unusually useful
  public infrastructure?
- **Realized public value:** did later evidence show that the value actually
  materialized?

Popularity alone is never public value. Raw stars, downloads, forks, roles,
claimed lineage strength, or host counts are not treated as proof.

## 3. Architecture and trust boundaries

The production architecture is intentionally only:

- `contracts/seedling.py`: GenLayer Intelligent Contract and canonical state;
- `frontend/`: React/Vite browser client using `genlayer-js` directly.

There is no backend, private database, server API, indexer, hidden ranking service,
fake-data fallback, or off-chain canonical state.

GenLayer comparative adjudication handles semantic questions such as uniqueness,
independent reuse, substitutes, gaming risk, public value, causal lineage, and
appeals. Deterministic contract code handles validation, lifecycle transitions,
storage integrity, policy binding, funding caps, cumulative release, contributor
allocation, and replay protection.

Nondeterministic adjudication uses the verified API pattern:

```python
gl.nondet.web.render(url, mode="text")
gl.nondet.exec_prompt(prompt)
gl.eq_principle.prompt_comparative(leader_fn, principle)
```

Rendered pages are bounded and explicitly treated as untrusted evidence. Model
outputs are strict JSON, schema-validated, allowlisted, and stored only after all
validation succeeds.

## 4. Repository map

- `contracts/seedling.py` — complete Intelligent Contract. Treat as frozen unless
  a user explicitly approves contract changes and understands that deployed code
  is immutable.
- `tests/direct/` — direct in-process GenVM tests for all contract stages.
- `tests/conftest.py` — Windows-only `gltest` cleanup compatibility shim; it affects
  the test harness only, not contract behavior or assertions.
- `docs/CONTRACT_INTERFACE.md` — frozen constructor, complete ABI, method argument
  ordering, return conventions, lifecycle values, and expected errors.
- `docs/STUDIONET_DEPLOYMENT.md` — canonical and verification deployment
  provenance, manual deployment package, live verification boundary.
- `frontend/src/lib/contract.ts` — canonical frontend method inventory, ordered
  arguments, direct reads, wallet writes, and finalized-receipt handling.
- `frontend/src/context/WalletContext.tsx` — wallet connection and StudioNet state.
- `frontend/src/pages/Pages.tsx` — application routes and protocol views/forms.
- `frontend/.env.example` — canonical public frontend configuration.
- `frontend/vercel.json` — SPA fallback required so direct links such as `/status`
  and `/discover` do not return Vercel 404s.
- `frontend/.gitignore` — ignores local `.vercel` metadata and `.env*` files. The
  already tracked `.env.example` remains in Git.

## 5. Contract model

Storage uses GenLayer `u256` counters and `TreeMap[str, str]` JSON records.
Identifiers are monotonic, one-based decimal strings. Per-candidate indexes store
bounded JSON ID arrays; public lists clamp page size to 50.

Primary canonical records include:

- `PublicGoodCandidate`
- `ObservationPolicy` and immutable version history
- `FundingPolicy` and immutable version history
- `EvidenceRecord` for latent and checkpoint evidence
- `LatentValueAssessment`
- `ContributionNode`
- `LineageEdge`
- `ImpactCheckpoint`
- realized-impact verdicts
- lineage verdicts and contributor attribution
- deterministic funding calculations
- appeals
- checkpoint finalization records

Important invariants:

- no silent overwrite, record deletion, or arbitrary owner rewrite;
- frozen evidence is immutable and future submissions are rejected;
- bound historical policy versions remain usable after deactivation;
- duplicate URL/hash evidence and contribution artifacts are scoped and rejected;
- source hosts are normalized so port changes cannot fake host diversity;
- host diversity is only a preliminary gate, not organizational independence;
- lineage nodes/edges are append-only claims, not attribution proof;
- self-loops, exact duplicate edges, and directed cycles are rejected;
- contributor and submitter are recorded separately;
- funding arithmetic is deterministic, monotonic, capped, and cannot double-release;
- finalized or voided checkpoints reject replay;
- owner authority is limited to global pause/unpause.

## 6. Lifecycle summary

Candidate importance lifecycle:

```text
DISCOVERED -> LATENT -> WATCHING -> EMERGING -> MATERIAL -> SYSTEMIC
```

Terminal/decline states also include `STALLED`, `DECLINED`, and `ARCHIVED`.

Key transitions:

- candidate registration creates `DISCOVERED`;
- successful latent-evidence freeze moves `DISCOVERED -> LATENT`;
- successful latent adjudication moves `LATENT -> WATCHING`;
- checkpoint opening/freezing does not promote importance;
- realized public-value adjudication controls later importance transitions;
- lineage registration alone never changes candidate importance.

Checkpoint status vocabulary includes:

```text
OPEN -> EVIDENCE_FROZEN -> EVALUATED/EVALUATING
     -> PUBLIC_VALUE_SET -> LINEAGE_SET -> FINALIZED or VOIDED
```

Appeal statuses are `OPEN`, `EVALUATING`, and `RESOLVED`.

## 7. Stage history

The implementation was built incrementally and kept functional after every stage:

| Stage | Scope | Commit |
|---|---|---|
| 1 | storage scaffold, protocol controls, test foundation | `eac9679` |
| 2 | candidates, ObservationPolicy, FundingPolicy | `89fc4ec` |
| 3 | candidate evidence and latent freeze | `038ed51` |
| 4 | GenLayer latent-value adjudication | `81db51e` |
| 5 | contribution nodes and lineage-edge claims | `484d7bd` |
| 6 | impact checkpoints and checkpoint evidence | `894f6f8` |
| 7 | public-value and anti-gaming adjudication | `a6a2903` |
| 8 | lineage adjudication and contributor attribution | `240acc6` |
| 9 | progressive dormant-funding accounting | `ec1ee84` |
| 10 | appeals and checkpoint finalization | `43a1348` |
| 11 | storage bounds and release-safety hardening | `daab601` |
| 12 | final contract integration/deployment audit | `5074f17` |
| 13 | production GenLayer frontend foundation | `143d658` |
| 14 | deployment verification and frontend binding | `d94fb41` onward |

Canonical manual-deployment and release commits:

- `bfa0c2b` — owner-controlled deployment package
- `5e07c86` — canonical manual address binding
- `6a553fb` — Vercel SPA deep-link support
- `1557217` / `06f3ace` — production links and metadata cleanup
- `3fb75f6` — ignore local Vercel metadata; final handover baseline

## 8. Production frontend

The frontend uses one contract-address configuration path:

```env
VITE_SEEDLING_CONTRACT_ADDRESS=0x72C0Ee823D32905f5D0b36a182Cfa526eA2e08aC
VITE_GENLAYER_NETWORK=studionet
```

These variables are configured in Vercel Production. Vite variables are public
configuration, not secrets. Never place wallet private keys in Vercel or frontend
environment variables.

Main routes:

- `/` — product thesis and lifecycle
- `/discover` — candidate discovery
- `/register` — candidate registration
- `/candidates/:candidateId` — complete candidate history
- `/candidates/:candidateId/evidence`
- `/candidates/:candidateId/checkpoints`
- `/candidates/:candidateId/checkpoints/:checkpointId`
- `/candidates/:candidateId/lineage`
- `/candidates/:candidateId/funding`
- `/candidates/:candidateId/appeals`
- `/methodology`
- `/status`

Writes display `submitting -> submitted -> consensus -> finalized`. Submission is
never presented as success. Success requires a finalized GenLayer receipt. Wallet
rejections and contract failures remain visible and do not create optimistic
canonical state.

The deployed production root and direct SPA routes `/status` and `/discover` were
verified to return HTTP 200. The deployed bundle was verified to contain the
canonical manual contract address. The public alias was also checked without
Vercel credentials and returned HTTP 200.

## 9. Quality gates and commands

Run from the repository root unless otherwise stated.

Contract tests:

```powershell
python -m pytest tests/ -q
```

Expected handover baseline: 254 passed, 0 failed. A Windows pytest-cache warning
may occur because `.pytest_cache` creation is denied; it does not affect tests.

GenVM gates on Windows:

```powershell
$env:PYTHONIOENCODING='utf-8'
$env:PYTHONUTF8='1'
genvm-lint check contracts/seedling.py
genvm-lint validate contracts/seedling.py
genvm-lint typecheck contracts/seedling.py
genvm-lint schema contracts/seedling.py
```

Expected results:

- lint passes two checks;
- validation passes;
- typecheck finds no errors;
- schema reports `Seedling`, zero constructor parameters, and 56 methods;
- the known `time.time()` nondeterminism warning remains. GenVM supplies the
  consensus clock; this warning was accepted throughout the audited build.

Frontend gates:

```powershell
cd frontend
npm run typecheck
npm run lint
npm test
npm run build
```

Expected baseline: 11 frontend tests pass; TypeScript, ESLint, and Vite production
build pass. The last verified build transformed 494 modules.

Integrity checks:

```powershell
git status --short
git diff --check
Get-FileHash contracts/seedling.py -Algorithm SHA256
```

Do not update dependencies casually. The deployed contract cannot be upgraded in
place, and frontend dependency changes should be tested against StudioNet behavior.

## 10. Live read verification

Read-only CLI examples:

```powershell
genlayer call 0x72C0Ee823D32905f5D0b36a182Cfa526eA2e08aC get_protocol_info
genlayer call 0x72C0Ee823D32905f5D0b36a182Cfa526eA2e08aC list_candidates --args 0 10
genlayer call 0x72C0Ee823D32905f5D0b36a182Cfa526eA2e08aC list_observation_policies --args 0 10
genlayer call 0x72C0Ee823D32905f5D0b36a182Cfa526eA2e08aC list_funding_policies --args 0 10
genlayer schema 0x72C0Ee823D32905f5D0b36a182Cfa526eA2e08aC
```

At handover the canonical deployment was intentionally empty: candidate,
observation-policy, and funding-policy lists each returned zero items. Do not add
fake records merely to make the UI look populated.

## 11. GitHub and Vercel operations

Git remote:

```text
origin https://github.com/Chinny070/seedling.git
branch master
```

The repository is public. Local `master` and `origin/master` were synchronized at
handover.

Vercel:

- account: `chinny070`
- project: `chinny070s-projects/seedling`
- stable production alias: https://seedling-lovat.vercel.app
- project directory: `frontend/`
- framework: Vite
- production environment includes both `VITE_` variables shown above.

Useful read-only checks:

```powershell
vercel env ls production
vercel inspect https://seedling-lovat.vercel.app
```

Do not run `vercel deploy --prod`, change environment variables, create GitHub
releases, or push commits without explicit user authorization.

## 12. Known verification boundary

The in-app browser controller could not initialize because its trusted browser
service dependency was unavailable. Production was instead verified through:

- Vercel deployment status (`READY`);
- authenticated Vercel HTTP requests;
- unauthenticated public HTTP request;
- deep-link route checks;
- deployed-bundle canonical-address inspection;
- direct StudioNet contract reads;
- automated wallet/network/transaction tests.

Real injected-wallet behavior still benefits from a human browser smoke test:

1. connect and reconnect a wallet;
2. verify account-change handling;
3. verify wrong-network detection and StudioNet switching;
4. reject a transaction and confirm the UI reports rejection;
5. perform only an intentional real protocol write, then confirm consensus and
   finalization states.

Do not create arbitrary production data just for smoke testing.

## 13. Safe continuation checklist

Before any future task:

1. read this file, `README.md`, `docs/CONTRACT_INTERFACE.md`, and the relevant
   source/tests;
2. run `git status --short` and preserve unrelated user changes;
3. confirm whether the requested action is read-only, code-only, on-chain, GitHub,
   or Vercel state mutation;
4. obtain explicit authorization for deployment, production environment changes,
   pushes/releases, or on-chain writes;
5. never guess GenLayer APIs—inspect installed SDK/tooling or authoritative docs;
6. keep contract ABI/storage backward-compatible unless the user explicitly accepts
   a new deployment and migration plan;
7. run proportional tests, lint, validation, typecheck, and production build;
8. verify that `contracts/seedling.py` did not change unintentionally;
9. update deployment docs only with facts that were directly verified;
10. return exact hashes, URLs, test totals, and any manual verification remaining.

## 14. Immediate handover state

At handover:

- canonical contract is live and unpaused;
- canonical state is empty;
- frontend production deployment is live and publicly accessible;
- GitHub repository is public;
- Vercel production variables point to the canonical contract;
- no backend or fake production data exists;
- application code has not been modified for this handover document;
- no contract or frontend redeployment was performed while creating this file.
