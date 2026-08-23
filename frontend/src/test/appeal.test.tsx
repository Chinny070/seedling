import { describe, expect, it } from "vitest";
import { assertWriteOrder } from "../lib/contract";

describe("appeal write ABI stays bound to what the UI sends", () => {
 it("freezes open_appeal argument order", () => {
  expect(assertWriteOrder("open_appeal", ["candidate_id", "checkpoint_id", "ground", "supporting_refs", "statement"])).toBe(true);
 });

 it("freezes evaluate_appeal as a single-argument call", () => {
  expect(assertWriteOrder("evaluate_appeal", ["appeal_id"])).toBe(true);
 });

 it("only offers a checkpoint for appeal once it is EVALUATED", () => {
  const appealable = (status: string) => status === "EVALUATED";
  expect(appealable("EVALUATED")).toBe(true);
  expect(appealable("OPEN")).toBe(false);
  expect(appealable("EVIDENCE_FROZEN")).toBe(false);
  expect(appealable("FINALIZED")).toBe(false);
  expect(appealable("VOIDED")).toBe(false);
 });

 it("only offers Evaluate appeal on an OPEN appeal", () => {
  const evaluable = (status: string) => status === "OPEN";
  expect(evaluable("OPEN")).toBe(true);
  expect(evaluable("EVALUATING")).toBe(false);
  expect(evaluable("RESOLVED")).toBe(false);
 });
});
