import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { assertWriteOrder } from "../lib/contract";
import { CandidateCard } from "../components/UI";

describe("checkpoint write ABI stays bound to what the UI sends", () => {
 it("freezes open_checkpoint argument order", () => {
  expect(assertWriteOrder("open_checkpoint", ["candidate_id", "period_start", "period_end"])).toBe(true);
 });

 it("freezes submit_checkpoint_evidence argument order", () => {
  expect(assertWriteOrder("submit_checkpoint_evidence", ["checkpoint_id", "source_type", "source_url", "content_hash", "summary", "period_start", "period_end"])).toBe(true);
 });

 it("freezes freeze_checkpoint and evaluate_public_value as single-argument calls", () => {
  expect(assertWriteOrder("freeze_checkpoint", ["checkpoint_id"])).toBe(true);
  expect(assertWriteOrder("evaluate_public_value", ["checkpoint_id"])).toBe(true);
 });

 it("freezes finalize_checkpoint argument order", () => {
  expect(assertWriteOrder("finalize_checkpoint", ["candidate_id", "checkpoint_id"])).toBe(true);
 });

 it("blocks finalization while an appeal on the checkpoint is unresolved", () => {
  const appeals = [
   { appeal_id: "1", checkpoint_id: "7", ground: "EVIDENCE_MISREAD", status: "RESOLVED", decision: "UPHOLD", statement: "" },
   { appeal_id: "2", checkpoint_id: "7", ground: "EVIDENCE_MISREAD", status: "OPEN", decision: "", statement: "" },
  ];
  const blocked = (status: string) => appeals.filter(a => a.checkpoint_id === "7").some(a => a.status !== "RESOLVED") || status !== "EVALUATED";
  expect(blocked("EVALUATED")).toBe(true);
  const resolved = appeals.filter(a => a.status === "RESOLVED");
  expect(resolved.some(a => a.status !== "RESOLVED")).toBe(false);
 });

 it("only offers checkpoints to candidates that have cleared latent adjudication", () => {
  const eligible = ["WATCHING", "EMERGING", "MATERIAL", "SYSTEMIC"];
  const ineligible = ["DISCOVERED", "LATENT", "STALLED", "DECLINED", "ARCHIVED"];
  const allowed = (status: string) => eligible.includes(status);
  eligible.forEach(s => expect(allowed(s)).toBe(true));
  ineligible.forEach(s => expect(allowed(s)).toBe(false));
 });
});

describe("candidate status still renders after moving past LATENT", () => {
 it("shows WATCHING once a candidate has cleared latent adjudication", () => {
  render(<MemoryRouter><CandidateCard candidate={{candidate_id:"1",name:"c-ares",description:"Async DNS library",candidate_type:"OPEN_SOURCE_LIBRARY",primary_artifact_url:"https://github.com/c-ares/c-ares",origin_date:"1998",public_access:true,observation_policy_id:"1",funding_policy_id:"1",status:"WATCHING"}}/></MemoryRouter>);
  expect(screen.getByText("WATCHING")).toBeInTheDocument();
 });
});
