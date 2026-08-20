# Canonical StudioNet deployment

## Owner-controlled canonical deployment

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
owner-controlled address.
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
