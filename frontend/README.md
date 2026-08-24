# SEEDLING frontend

Production React/Vite client for the SEEDLING Intelligent Contract. The browser
calls GenLayer directly through `genlayer-js`; there is no API server, database,
indexer, or off-chain source of canonical protocol state.

## Configuration

Copy `.env.example` to `.env.local`. The checked-in address is the owner's
canonical manual StudioNet deployment:

```env
VITE_SEEDLING_CONTRACT_ADDRESS=0xe2A8BC5659D863158e9C500B71762a7ba4C77F84
VITE_GENLAYER_NETWORK=studionet
```

No fallback or fake address is supplied. The earlier Stage 14 address remains a
verification deployment only. The UI displays a clear configuration state if the
canonical variable is absent or malformed and never substitutes demo records. Do
not put wallet private keys in frontend environment variables. Deployment
provenance is recorded in `../docs/STUDIONET_DEPLOYMENT.md`.

StudioNet uses GenLayer RPC `https://studio.genlayer.com/api`, chain ID `61999`,
and currency `GEN`. Network configuration comes from `genlayer-js/chains` rather
than a hand-maintained chain object.

## Local development

```bash
cd frontend
npm install
npm run dev
```

Quality gates:

```bash
npm run typecheck
npm run lint
npm test
npm run build
```

## Architecture

- `src/lib/contract.ts` freezes all 33 read and 23 write method names and ordered
  arguments from `docs/CONTRACT_INTERFACE.md`.
- `src/context/WalletContext.tsx` handles disconnected, connecting, connected,
  wrong-network, and switch-network states.
- Contract reads are direct and JSON-normalized in the browser.
- Writes progress through `submitting → submitted → consensus → finalized`.
  Submission is never displayed as success; success requires
  `waitForTransactionReceipt(..., FINALIZED)`.
- Rejections and reverts remain visible and do not create optimistic canonical state.
- All live pages show loading, empty, configuration, and RPC/error states.

The frontend does not render arbitrary contract text as HTML. Public URLs open in
new tabs with `noopener` protection, and form inputs use browser constraints before
the contract performs authoritative validation.

## Routes

- `/` protocol thesis and lifecycle
- `/discover` live candidate discovery
- `/register` candidate transaction
- `/candidates/:candidateId` complete candidate history
- `/candidates/:candidateId/evidence` evidence reads/submission
- `/candidates/:candidateId/checkpoints` checkpoint history
- `/candidates/:candidateId/checkpoints/:checkpointId` checkpoint detail
- `/candidates/:candidateId/lineage` provenance graph
- `/candidates/:candidateId/funding` accounting progression
- `/candidates/:candidateId/appeals` appeal history
- `/methodology` adjudication and funding methodology
- `/status` contract/network integration state

The UI is responsive at mobile (375px), tablet (768px), and wide desktop (1440px),
with semantic landmarks, keyboard focus, labelled forms, status/error live regions,
high contrast, and reduced-motion support.
