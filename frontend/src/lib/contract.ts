import { abi, createClient } from "genlayer-js";
import { studionet } from "genlayer-js/chains";
import { TransactionStatus } from "genlayer-js/types";

export type HexAddress = `0x${string}`;
export type ContractArg = string | number | boolean | string[];
export type TxPhase = "idle" | "submitting" | "submitted" | "consensus" | "finalized" | "rejected" | "failed";
export interface TxState { phase: TxPhase; hash?: string; message?: string }

export const NETWORK = { name: "StudioNet", id: 61999, hexId: "0xf22f" } as const;
export const contractAddress = import.meta.env.VITE_SEEDLING_CONTRACT_ADDRESS as string | undefined;
export const hasContract = Boolean(contractAddress && /^0x[0-9a-fA-F]{40}$/.test(contractAddress));

export const viewArgs = {
  get_protocol_info: [] as [], get_candidate: ["candidate_id"] as const,
  list_candidates: ["offset", "limit"] as const, get_evidence: ["evidence_id"] as const,
  list_candidate_evidence: ["candidate_id", "offset", "limit"] as const,
  get_latent_evidence_set: ["candidate_id"] as const, get_latent_assessment: ["assessment_id"] as const,
  list_candidate_latent_assessments: ["candidate_id", "offset", "limit"] as const,
  get_checkpoint: ["checkpoint_id"] as const, list_checkpoints: ["candidate_id", "offset", "limit"] as const,
  list_checkpoint_evidence: ["checkpoint_id", "offset", "limit"] as const,
  get_checkpoint_evidence_set: ["checkpoint_id"] as const, get_impact_verdict: ["verdict_id"] as const,
  list_checkpoint_impact_verdicts: ["checkpoint_id", "offset", "limit"] as const,
  get_lineage_verdict: ["lineage_verdict_id"] as const,
  list_candidate_lineage_verdicts: ["candidate_id", "offset", "limit"] as const,
  get_funding_calculation: ["funding_calculation_id"] as const,
  list_candidate_funding_calculations: ["candidate_id", "offset", "limit"] as const,
  get_candidate_funding_summary: ["candidate_id"] as const, get_appeal: ["appeal_id"] as const,
  list_candidate_appeals: ["candidate_id", "offset", "limit"] as const,
  get_funding_preview: ["checkpoint_id"] as const, get_checkpoint_finalization: ["checkpoint_id"] as const,
  get_contribution_node: ["node_id"] as const, list_contribution_nodes: ["candidate_id", "offset", "limit"] as const,
  get_lineage_edge: ["edge_id"] as const, list_lineage_edges: ["candidate_id", "offset", "limit"] as const,
  get_observation_policy: ["policy_id"] as const, list_observation_policies: ["offset", "limit"] as const,
  get_observation_policy_history: ["family_id"] as const, get_funding_policy: ["funding_policy_id"] as const,
  list_funding_policies: ["offset", "limit"] as const, get_funding_policy_history: ["family_id"] as const,
} as const;
export type ViewMethod = keyof typeof viewArgs;

export const writeArgs = {
  pause: [] as const, unpause: [] as const,
  create_observation_policy: ["name","candidate_types","minimum_evidence_categories","minimum_independent_sources","latent_rules","impact_rules","lineage_rules","gaming_rules","substitute_rules","checkpoint_interval"] as const,
  version_observation_policy: ["policy_id","name","candidate_types","minimum_evidence_categories","minimum_independent_sources","latent_rules","impact_rules","lineage_rules","gaming_rules","substitute_rules","checkpoint_interval"] as const,
  set_observation_policy_status: ["policy_id","active"] as const,
  create_funding_policy: ["name","latent_cap_bps","watching_cap_bps","emerging_cap_bps","material_cap_bps","systemic_cap_bps","minimum_public_value_bps","maximum_gaming_risk_bps","minimum_attribution_confidence_bps"] as const,
  version_funding_policy: ["funding_policy_id","name","latent_cap_bps","watching_cap_bps","emerging_cap_bps","material_cap_bps","systemic_cap_bps","minimum_public_value_bps","maximum_gaming_risk_bps","minimum_attribution_confidence_bps"] as const,
  set_funding_policy_status: ["funding_policy_id","active"] as const,
  register_candidate: ["name","description","candidate_type","primary_artifact_url","origin_date","public_access","observation_policy_id","funding_policy_id"] as const,
  submit_candidate_evidence: ["candidate_id","source_type","source_url","content_hash","summary","period_start","period_end"] as const,
  freeze_latent_evidence: ["candidate_id"] as const, evaluate_latent_value: ["candidate_id"] as const,
  open_checkpoint: ["candidate_id","period_start","period_end"] as const,
  submit_checkpoint_evidence: ["checkpoint_id","source_type","source_url","content_hash","summary","period_start","period_end"] as const,
  freeze_checkpoint: ["checkpoint_id"] as const, evaluate_public_value: ["checkpoint_id"] as const,
  register_contribution_node: ["candidate_id","contributor","artifact_type","artifact_url","artifact_hash","role","summary"] as const,
  register_lineage_edge: ["candidate_id","from_node_id","to_node_id","relationship_type","evidence_refs","claimed_strength_bps"] as const,
  evaluate_lineage: ["checkpoint_id"] as const, calculate_funding: ["checkpoint_id"] as const,
  open_appeal: ["candidate_id","checkpoint_id","ground","supporting_refs","statement"] as const,
  evaluate_appeal: ["appeal_id"] as const, finalize_checkpoint: ["candidate_id","checkpoint_id"] as const,
  preview_evidence_digest: ["url"] as const,
} as const;
export type WriteMethod = keyof typeof writeArgs;

type Provider = { request(args: { method: string; params?: unknown[] }): Promise<unknown> };

function requireAddress(): HexAddress {
  if (!hasContract) throw new Error("Set VITE_SEEDLING_CONTRACT_ADDRESS to the deployed StudioNet contract address.");
  return contractAddress as HexAddress;
}

export function normalizeContractResult(value: unknown): unknown {
  if (typeof value !== "string") return value;
  try { return JSON.parse(value); } catch { return value; }
}

const readSubjects: Partial<Record<ViewMethod, string>> = {
  get_candidate: "Candidate", get_checkpoint: "Checkpoint", get_evidence: "Evidence record",
  get_latent_assessment: "Latent assessment", get_impact_verdict: "Impact verdict",
  get_lineage_verdict: "Lineage verdict", get_funding_calculation: "Funding calculation",
  get_appeal: "Appeal", get_contribution_node: "Contribution node", get_lineage_edge: "Lineage edge",
  get_observation_policy: "Observation policy", get_funding_policy: "Funding policy",
};

/** Translate a raw RPC/client failure into product copy without inventing a result. */
export function describeReadError(method: ViewMethod, args: ContractArg[], error: unknown): string {
  const raw = error instanceof Error ? error.message : String(error);
  if (/failed to fetch|networkerror|network error|timeout|econn/i.test(raw))
    return `Could not reach ${NETWORK.name}. Nothing was read, so no cached or substitute data is shown.`;
  if (/execution failed|missing or invalid parameters|not found|out of range/i.test(raw)) {
    const subject = readSubjects[method];
    if (subject) return `${subject}${args.length ? ` #${String(args[0])}` : ""} was not found on the canonical contract.`;
    return "The canonical contract returned no record for this request.";
  }
  return "Contract read failed. No off-chain fallback data is shown.";
}

export function makeClient(account?: HexAddress, provider?: Provider) {
  return createClient({ chain: studionet, account, provider });
}

export async function readContract<T>(method: ViewMethod, args: ContractArg[] = []): Promise<T> {
  const value = await makeClient().readContract({ address: requireAddress(), functionName: method, args });
  return normalizeContractResult(value) as T;
}

export async function writeContract(
  account: HexAddress, provider: Provider, method: WriteMethod, args: ContractArg[],
  onState: (state: TxState) => void,
): Promise<unknown> {
  const client = makeClient(account, provider);
  try {
    onState({ phase: "submitting", message: "Confirm this transaction in your wallet." });
    const hash = await client.writeContract({ address: requireAddress(), functionName: method, args, value: 0n });
    onState({ phase: "submitted", hash, message: "Submitted. Waiting for validator consensus." });
    onState({ phase: "consensus", hash, message: "Validators are reaching consensus." });
    const receipt = await client.waitForTransactionReceipt({ hash, status: TransactionStatus.FINALIZED, interval: 2000, retries: 90 });
    onState({ phase: "finalized", hash, message: "Finalized by the GenLayer network." });
    return receipt;
  } catch (error) {
    const message = error instanceof Error ? error.message : "Transaction failed.";
    const rejected = /reject|denied|cancel/i.test(message);
    onState({ phase: rejected ? "rejected" : "failed", message });
    throw error;
  }
}

/** Pull a write method's return value out of its finalized receipt.
 *
 * GenLayer reports that value in more than one shape depending on which client
 * call produced the receipt, so all of them are handled rather than pinning the
 * one that happened to be observed:
 *   result.payload.readable  - what waitForTransactionReceipt returns, a
 *                              JSON-encoded string wrapping the JSON
 *   result.raw / result      - base64 of calldata-encoded bytes, as the
 *                              explorer query returns
 * Only methods that return something meaningful need this; every other write
 * ignores the receipt. Returns undefined rather than throwing on an unfamiliar
 * shape, so a decoding surprise degrades to "no preview" instead of breaking
 * submission.
 */
export function decodeWriteResult(receipt: unknown): unknown {
  type ResultShape = string | { raw?: string; payload?: { readable?: string } };
  const result = (receipt as { consensus_data?: { leader_receipt?: { result?: ResultShape }[] } })
    ?.consensus_data?.leader_receipt?.[0]?.result;
  if (!result) return undefined;

  if (typeof result === "object" && typeof result.payload?.readable === "string") {
    // Peel JSON encoding layers until a non-string falls out or nothing parses.
    let value: unknown = result.payload.readable;
    for (let depth = 0; depth < 3 && typeof value === "string"; depth++) {
      try { value = JSON.parse(value); } catch { break; }
    }
    return value;
  }

  const encoded = typeof result === "string" ? result : result.raw;
  if (typeof encoded !== "string" || !encoded) return undefined;
  let bytes: Uint8Array;
  try { bytes = Uint8Array.from(atob(encoded), ch => ch.charCodeAt(0)); } catch { return undefined; }
  for (const candidate of [bytes, bytes.slice(1), bytes.slice(2)]) {
    try { return abi.calldata.decode(candidate); } catch { /* try the next framing */ }
  }
  return undefined;
}

export function assertWriteOrder(method: WriteMethod, labels: readonly string[]): boolean {
  return JSON.stringify(writeArgs[method]) === JSON.stringify(labels);
}
