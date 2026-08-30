# Canonical StudioNet deployment

## Current canonical deployment

- Network: GenLayer StudioNet
- Chain ID: `61999`
- RPC: `https://studio.genlayer.com/api`
- Contract: `0x29b0e5724EFD1C1BB01666a17F1Ed9f0d0292eac`
- Owner: `0xaffE15eEc45b68835cc9E5B4Ab85dD5deaE8e70b`
- Deployment method: manually deployed by the owner in GenLayer Studio
- Constructor: `Seedling()` with zero arguments
- Deployed: 2026-08-30
- Source SHA-256: `d19d767ad243f9037d48a6aa0b98c8ace56f052ca08b364307a7d463d4ad2904`
  (hashed with LF line endings, as the file is stored in git)
- Source commit: `a21058e`
- Public ABI: 57 methods (33 views, 24 writes), zero-argument `Seedling()`
  constructor
- Adds one method: `preview_evidence_digest(url)`

### Why

The digest binding shipped in the deployment below is correct but unusable. The
value a submitter must supply as `content_hash` is derived from
`gl.nondet.web.render(url, mode="text")` - text that nothing off-chain
reproduces. A wrong digest is accepted at submission, survives the freeze, and
only surfaces as a rollback at adjudication, at which point the evidence set is
sealed and the candidate is spent.

That was confirmed in practice, not in theory: candidate #1 (c-ares) on
`0xF362...6f31` was registered with a digest computed from the archived bytes,
froze cleanly, and rolled back at `evaluate_latent_value` with
`EXPECTED: rendered content for evidence 1 does not match its submitted
digest`. The guard behaved correctly; the requirement was simply not
satisfiable in advance by anyone, including a reviewing steward.

`preview_evidence_digest` renders one url under strict equality and reports the
digest the adjudication paths will verify against, plus the rendered character
count and the first 800 characters. It grants no authority, writes no evidence,
and mutates no lifecycle state. It enforces the same archive-source rule as
submission, so a preview can never bless a url that submission would reject.

Verified live after deployment: `name: SEEDLING`, `owner` as above,
`paused: false`, protocol/spec version 1, all eleven counters at zero, and
empty candidate and policy pages. The deployment transaction hash was not
supplied and is therefore not asserted here.

## Superseded: evidence-integrity deployment

Superseded 2026-08-30 by the deployment above, which adds the digest preview
the rule needed to be usable. Holds candidate #1 (c-ares), one evidence row,
and one frozen latent evidence set that can never be adjudicated - the
rollback that motivated the preview method.

- Network: GenLayer StudioNet
- Chain ID: `61999`
- RPC: `https://studio.genlayer.com/api`
- Contract: `0xF3626A32B588B9F5Fc68C76ff4abc55f966E6f31`
- Owner: `0xaffE15eEc45b68835cc9E5B4Ab85dD5deaE8e70b`
- Deployment method: manually deployed by the owner in GenLayer Studio
- Constructor: `Seedling()` with zero arguments
- Deployed: 2026-08-29
- Source SHA-256: `43137aa662751edab6b1f4393521daced1c65b8ec5cd8cf418c088152fafbb7e`
  (hashed with LF line endings, as the file is stored in git)
- Git blob hash: `75aebb16db1797eb7dc78d8b9fc36c9a4f9a868a`
- Source commit: `cf1e8c2`
- Public ABI: unchanged — 56 methods (33 views, 23 writes), zero-argument
  `Seedling()` constructor

What changed, and why it required a new deployment:

1. **Submission time.** Evidence, checkpoint evidence, and contribution
   artifacts must now be raw Wayback snapshot URLs (`/web/<ts>id_/<origin>`),
   so the bytes behind a submitted URL cannot change after submission. The
   embedded origin URL is what source independence and duplicate detection are
   measured against, so archiving does not collapse every source onto
   `web.archive.org`.
2. **Adjudication time.** All four adjudication paths now verify the rendered
   text against the submitted `content_hash`/`artifact_hash` via
   `_render_digest`, and a mismatch or failed render aborts the transaction.
   Previously a failed render silently degraded to `[content unavailable]`,
   which meant judging content nobody had attested to.

Both rules are consensus-affecting and reject data the previous deployment
accepts, so the previous deployment's records could not be migrated. This
deployment starts empty and the lifecycle must be re-exercised end to end.

Verified live after deployment via the frontend's installed `genlayer-js`
client: `name: SEEDLING`, `owner` as above, `paused: false`, protocol/spec
version 1, all eleven counters at zero, and empty `list_candidates`,
`list_observation_policies`, and `list_funding_policies` pages. The deployment
transaction hash was not supplied and is therefore not asserted here.

The frontend also now exposes `finalize_checkpoint`, which existed on-chain
from the start but had no UI surface — without it the repeated funding
lifecycle could not be completed from the product. That change is frontend-only
and needs no redeployment on its own.

## Superseded: prompt-fix deployment

Superseded 2026-08-29 by the evidence-integrity deployment above. Holds
whatever lifecycle records were created against it; none of them satisfy the
archive-source or digest-binding rules, which is why they were not migrated.

- Network: GenLayer StudioNet
- Chain ID: `61999`
- RPC: `https://studio.genlayer.com/api`
- Contract: `0xe2A8BC5659D863158e9C500B71762a7ba4C77F84`
- Owner: `0xaffE15eEc45b68835cc9E5B4Ab85dD5deaE8e70b`
- Deployment method: manually deployed by the owner
- Constructor: `Seedling()` with zero arguments
- Source SHA-256: `5ea0fe79a5cd0f22f6cff3f80c10f279806817cba7ff25ecb82e87c7396a2002`
- Git blob hash: `df9f75c065e43b6b63d5abdc0840326f69171294`
- Deployed: 2026-08-24

Verified live after deployment: `name: SEEDLING`, `owner` as above,
`paused: false`, protocol/spec version 1, all eleven counters at zero, and an
on-chain schema of exactly 56 methods (33 view, 23 write) with a zero-argument
constructor — ABI-identical to the superseded deployments.

### Why this deployment exists

The previous deployment's public-value equivalence-principle fix worked —
consensus was reached repeatedly — but real testing surfaced a second,
separate defect: the `evaluate_public_value` prompt never told the model a
character limit for the `summary` field, unlike the latent and appeal
prompts, which state it explicitly. Every attempt that reached agreement
overran `MAX_IMPACT_SUMMARY_LEN` (1000) and rolled back.

Because this defect class (a principle fix landing while an unrelated
missing-instruction defect kept causing failures) had already occurred once
for `evaluate_appeal`, all four adjudication prompts in the contract were
audited this time, not just the one that had just failed. `evaluate_lineage`
had the identical gap — no character-limit instruction for `summary` — even
though it had already succeeded once on the previous deployment; that one
success does not establish the gap was safe, only that it had not yet been
hit. `evaluate_latent_value` and `evaluate_appeal` already stated the limit
correctly and needed no change.

This deployment adds one sentence to each of the `evaluate_public_value` and
`evaluate_lineage` prompts, stating the summary field's character limit
explicitly, matching the instruction pattern already used by
`evaluate_latent_value` and `evaluate_appeal`. No principle, storage layout,
method signature, validation rule, or ABI entry changed.

### Known remaining risk

Appeal adjudication (`evaluate_appeal`) has prompt fixes from two prior
deployments (explicit UPHOLD-preservation instruction, explicit summary
length cap) that have not yet been exercised against a live run on any
deployment. If it fails in the same ways again despite the fixes, or in a
new way, that finding should be recorded here before any further
deployment.

## Superseded canonical deployments

Retained as the record of the findings above. None should be used as the
frontend or submission address.

- Contract: `0x05f43D86d7fa8044647073D089652F3Bbb619fE6`
- Source SHA-256: `acc1a4b04a699f87440a36c0604a17cbd2bae0be730e18adf65d162a66f7876c`
- Git blob hash: `70f315b96285c47818c1e44acf9ede10b0d1ceab`
- Deployed: 2026-08-23 — superseded 2026-08-24 (missing summary-length
  instructions in the public-value and lineage prompts)
- Holds: one candidate (curl), six evidence records, one checkpoint, one
  finalized latent assessment (retried once), no finalized impact verdict
  (repeated `evaluate_public_value` rollbacks from oversized summaries once
  consensus started landing)

- Contract: `0x98bEbFDf7E119551De3F83CC89b1b61130ECFf70`
- Source SHA-256: `44bda47a16f6d27213e42e01c82537c4a6e48a083faf2de999d45cb016a35e1b`
- Git blob hash: `2f5b341d5bbc4bdb3152b9ece19b0416d1b4e62c`
- Deployed: 2026-08-23 — superseded 2026-08-23 (public-value adjudication fix)
- Holds: one candidate (curl), six evidence records, one checkpoint, one
  finalized latent assessment, no finalized impact verdict (8 consecutive
  `evaluate_public_value` attempts failed against the unmodified principle),
  one policy of each kind

- Contract: `0xA01aF2fc2fd41775A0F6f4C64d4064B3b98354f8`
- Source SHA-256: `9e6213328072b3a83e680e7186d5e758f5952dc684fc2c05d72e6b71e7c86462`
- Git blob hash: `42f4e7a755c01fb5b8cb66ebfe45702b7980b419`
- Deployed: 2026-08-23 — superseded 2026-08-23 (appeal prompt fix)
- Holds: one candidate (curl), six evidence records, one checkpoint, one
  finalized latent assessment, one finalized impact verdict (SYSTEMIC), two
  contribution nodes, one lineage edge, one finalized lineage verdict
  (50/50 split), one funding calculation (10000/10000 bps), one open,
  unresolved appeal, one policy of each kind

- Contract: `0x9f4675FfA027eBB82Bb60182F40FDBAB7038F766`
- Source SHA-256: `e5375ac518994d9d73ff9f60214fd4822617d0f36d5d69bc1193ae971dbfd3a4`
- Git blob hash: `d485304d6e463f7e9167d9000e8131e1c1da2cbe`
- Deployed: 2026-08-21 — superseded 2026-08-23 (lineage adjudication fix)
- Holds: two candidates (c-ares, curl), twelve evidence records, one
  checkpoint each, one finalized latent assessment each, one finalized
  impact verdict (curl, SYSTEMIC), two contribution nodes and one lineage
  edge on curl, one policy of each kind

- Contract: `0x72C0Ee823D32905f5D0b36a182Cfa526eA2e08aC`
- Source SHA-256: `4fb7bb560c445d35c180f62c067624905386431f5bb0311aac3b19193cbb7873`
- Git blob hash: `8af172dc01fac4da64a10dc61c8e659c32fcbf48`
- Deployed: 2026-08-20 — superseded 2026-08-21 (latent adjudication fix)
- Holds: two candidates, six evidence records, one policy of each kind

## Original owner-controlled deployment notes

### Owner-controlled canonical deployment (superseded)

- Network: GenLayer StudioNet
- Chain ID: `61999`
- RPC: `https://studio.genlayer.com/api`
- Contract: `0x72C0Ee823D32905f5D0b36a182Cfa526eA2e08aC`
- Owner: `0xaffE15eEc45b68835cc9E5B4Ab85dD5deaE8e70b`
- Deployment method: manually deployed by the owner in GenLayer Studio
- Constructor: `Seedling()` with zero arguments
- Source SHA-256: `4fb7bb560c445d35c180f62c067624905386431f5bb0311aac3b19193cbb7873`
- Git blob hash: `8af172dc01fac4da64a10dc61c8e659c32fcbf48`

Live verification confirmed `name: SEEDLING`, `paused: false`, protocol/spec
version 1, empty initial state, the owner above, and the expected zero-argument,
56-method ABI. The deployment transaction hash was not supplied and is therefore
not asserted here.

Production frontend: https://seedling-lovat.vercel.app
Source repository: https://github.com/Chinny070/seedling

## Earlier verification deployment

SEEDLING was deployed exactly once for Stage 14 from the frozen Stage 13 contract.
That deployment is verification-only and is **not** the final canonical submission
deployment. No constructor arguments or production records were supplied. The
owner subsequently performed the canonical deployment manually in GenLayer Studio.

### Verification provenance

- Network: GenLayer StudioNet
- Chain ID: `61999`
- RPC: `https://studio.genlayer.com/api`
- Verification-only contract: `0xcb2FfAC9E22dfE582Ab3A9F45CcA1FAB0cEC1D25`
- Transaction: `0xf5e1e10a27daa764bcd282d11bf585a2d43ac536d50b38a84ee101108f1ecb99`
- Deployer: `0x13AE0C28D06716D2908B5d84c3c0c3d815378f3B`
- Deployed at: `2026-08-20T11:19:31.555122+00:00`
- Source commit: `143d658fe1a1cd5b08db11756281245fca2ff6e5`
- Git blob hash (`contracts/seedling.py`): `8af172dc01fac4da64a10dc61c8e659c32fcbf48`
- Constructor: `Seedling()` with zero arguments
- Result: `ACCEPTED`, `MAJORITY_AGREE`, one round

The verification transaction contained the audited source from the commit above.
This address must not be used as the canonical frontend or submission address
unless the owner explicitly reverses that decision.

## Final audited manual-deployment package

- File to open or copy: `contracts/seedling.py`
- Contract class: `Seedling`
- Constructor: `Seedling()`
- Constructor arguments: none
- SHA-256: `4fb7bb560c445d35c180f62c067624905386431f5bb0311aac3b19193cbb7873`
- Git blob hash: `8af172dc01fac4da64a10dc61c8e659c32fcbf48`
- Public ABI: 56 methods (33 views, 23 writes)

Manual deployment procedure:

1. Open GenLayer Studio and select StudioNet (chain ID `61999`).
2. Create/open an Intelligent Contract deployment editor.
3. Open `contracts/seedling.py` locally and copy the complete file exactly,
   beginning with the `# v0.2.16` pragma and dependency header.
4. Paste it into the Studio contract editor without modifying it.
5. Select the `Seedling` contract if Studio asks for the contract class.
6. Leave constructor arguments empty; `Seedling()` takes zero parameters.
7. Connect the wallet/account that should control the deployment and confirm that
   StudioNet is selected.
8. Deploy once and wait for the transaction to finalize.
9. Record the new contract address and transaction hash, then provide the address
   for frontend configuration and production verification.

Do not paste a private key into the source or frontend environment. The constructor
sets the contract owner from the deployment sender, so deployment from your wallet
is what gives that address the protocol's owner-only pause/unpause authority.

## Live verification

Read-only calls were executed against the verification address after finalization:

- `get_protocol_info()` returned `SEEDLING`, owner matching the deployer,
  `paused: false`, protocol/spec version 1, and zero initial records.
- `list_candidates(0, 10)` returned `{"items": [], "total": 0}`.
- `list_observation_policies(0, 10)` returned an empty bounded page.
- `list_funding_policies(0, 10)` returned an empty bounded page.
- The live schema reports a zero-argument constructor and 56 public methods:
  33 views and 23 writes.

Item-level policy reads are not applicable because the verification deployment is
intentionally empty. Stage 14 did not create arbitrary policies, candidates, or
other production records merely to populate read results.

## Frontend binding

The single frontend configuration path remains
`VITE_SEEDLING_CONTRACT_ADDRESS`. `frontend/.env.example` contains the canonical
owner-controlled address, now
`0x29b0e5724EFD1C1BB01666a17F1Ed9f0d0292eac`. The Vercel project environment
variable must be updated to match and the project rebuilt — the Vite variable is
inlined at build time, so saving it without a rebuild leaves the old address
live.
StudioNet configuration comes from `genlayer-js/chains` and targets chain 61999.
There is no backend, database, indexer, private key, or fake-data fallback.

## Verification boundary

Automated frontend tests and production build verify configuration handling,
direct contract reads, wallet state logic, transaction finality semantics, and
error/rejection presentation. Live reads were confirmed both with the StudioNet
CLI and through the frontend's installed `genlayer-js` client; the SDK returned
`SEEDLING`, `paused: false`, and a zero-candidate verification state.

Injected-wallet interaction remains **NOT YET MANUALLY VERIFIED** in this
environment because the browser-control runtime cannot load its trusted browser
service dependency. The following checks remain for a human browser session:

1. connect and reconnect an injected wallet;
2. account-change handling;
3. wrong-network detection and StudioNet switching;
4. user rejection of a write request;
5. one intentional, valid production write and finalized receipt, if/when an
   operator chooses to create real protocol data.

No write was sent during verification, preserving the verification deployment's
empty state and avoiding fabricated production history.
