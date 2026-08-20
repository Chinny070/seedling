# Canonical StudioNet deployment

SEEDLING was deployed exactly once for Stage 14 from the frozen Stage 13 contract.
No constructor arguments or production records were supplied.

## Provenance

- Network: GenLayer StudioNet
- Chain ID: `61999`
- RPC: `https://studio.genlayer.com/api`
- Contract: `0xcb2FfAC9E22dfE582Ab3A9F45CcA1FAB0cEC1D25`
- Transaction: `0xf5e1e10a27daa764bcd282d11bf585a2d43ac536d50b38a84ee101108f1ecb99`
- Deployer: `0x13AE0C28D06716D2908B5d84c3c0c3d815378f3B`
- Deployed at: `2026-08-20T11:19:31.555122+00:00`
- Source commit: `143d658fe1a1cd5b08db11756281245fca2ff6e5`
- Git blob hash (`contracts/seedling.py`): `8af172dc01fac4da64a10dc61c8e659c32fcbf48`
- Constructor: `Seedling()` with zero arguments
- Result: `ACCEPTED`, `MAJORITY_AGREE`, one round

The deployment transaction contained the audited source from the commit above.
`contracts/seedling.py` was not changed during Stage 14.

## Live verification

Read-only calls were executed against the canonical address after finalization:

- `get_protocol_info()` returned `SEEDLING`, owner matching the deployer,
  `paused: false`, protocol/spec version 1, and zero initial records.
- `list_candidates(0, 10)` returned `{"items": [], "total": 0}`.
- `list_observation_policies(0, 10)` returned an empty bounded page.
- `list_funding_policies(0, 10)` returned an empty bounded page.
- The live schema reports a zero-argument constructor and 56 public methods:
  33 views and 23 writes.

Item-level policy reads are not applicable because the canonical deployment is
intentionally empty. Stage 14 did not create arbitrary policies, candidates, or
other production records merely to populate read results.

## Frontend binding

The single frontend configuration path remains
`VITE_SEEDLING_CONTRACT_ADDRESS`. The canonical value is recorded in
`frontend/.env.example`; local operators copy that file to `.env.local`.
StudioNet configuration comes from `genlayer-js/chains` and targets chain 61999.
There is no backend, database, indexer, private key, or fake-data fallback.

## Verification boundary

Automated frontend tests and production build verify configuration handling,
direct contract reads, wallet state logic, transaction finality semantics, and
error/rejection presentation. Live reads were confirmed both with the StudioNet
CLI and through the frontend's installed `genlayer-js` client; the SDK returned
`SEEDLING`, `paused: false`, and a zero-candidate canonical state.

Injected-wallet interaction remains **NOT YET MANUALLY VERIFIED** in this
environment because the browser-control runtime cannot load its trusted browser
service dependency. The following checks remain for a human browser session:

1. connect and reconnect an injected wallet;
2. account-change handling;
3. wrong-network detection and StudioNet switching;
4. user rejection of a write request;
5. one intentional, valid production write and finalized receipt, if/when an
   operator chooses to create real protocol data.

No write was sent during deployment verification, preserving the empty canonical
state and avoiding fabricated production history.
