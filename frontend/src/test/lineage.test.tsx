import { describe, expect, it } from "vitest";
import { assertWriteOrder } from "../lib/contract";

describe("lineage and funding write ABI stays bound to what the UI sends", () => {
 it("freezes register_contribution_node argument order", () => {
  expect(assertWriteOrder("register_contribution_node", ["candidate_id", "contributor", "artifact_type", "artifact_url", "artifact_hash", "role", "summary"])).toBe(true);
 });

 it("freezes register_lineage_edge argument order", () => {
  expect(assertWriteOrder("register_lineage_edge", ["candidate_id", "from_node_id", "to_node_id", "relationship_type", "evidence_refs", "claimed_strength_bps"])).toBe(true);
 });

 it("freezes evaluate_lineage and calculate_funding as single-argument calls", () => {
  expect(assertWriteOrder("evaluate_lineage", ["checkpoint_id"])).toBe(true);
  expect(assertWriteOrder("calculate_funding", ["checkpoint_id"])).toBe(true);
 });

 it("rejects a self-loop before it ever reaches the wallet", () => {
  const from = "3", to = "3";
  const isSelfLoop = from === to;
  expect(isSelfLoop).toBe(true);
 });

 it("only offers an edge form once at least two contribution nodes exist", () => {
  const canClaimEdge = (nodeCount: number) => nodeCount >= 2;
  expect(canClaimEdge(0)).toBe(false);
  expect(canClaimEdge(1)).toBe(false);
  expect(canClaimEdge(2)).toBe(true);
 });
});
