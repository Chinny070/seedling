import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { LatentStage } from "../pages/Pages";
import { toEpoch } from "../lib/records";
import type { LatentSet } from "../lib/records";

const base: LatentSet = {
 candidate_id: "1", frozen: false, candidate_status: "DISCOVERED",
 evidence_count: 0, distinct_category_count: 0, distinct_categories: [],
 distinct_host_count: 0, distinct_hosts: [],
 minimum_evidence_categories: 3, minimum_independent_sources: 2,
 requirements_met: false,
};

const show = (set: Partial<LatentSet>, onRun = vi.fn()) => {
 render(<LatentStage set={{ ...base, ...set }} locked={false} onRun={onRun} />);
 return onRun;
};

describe("latent stage gating", () => {
 it("reports progress toward the bound policy thresholds", () => {
  show({ evidence_count: 2, distinct_category_count: 2, distinct_host_count: 1 });
  expect(screen.getByText("2/3")).toBeInTheDocument();
  expect(screen.getByText("1/2")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Freeze latent evidence" })).toBeDisabled();
 });

 it("enables freezing only once the policy thresholds are met", async () => {
  const onRun = show({ evidence_count: 3, distinct_category_count: 3, distinct_host_count: 2, requirements_met: true });
  const button = screen.getByRole("button", { name: "Freeze latent evidence" });
  expect(button).toBeEnabled();
  expect(screen.getByText(/Freezing is irreversible/)).toBeInTheDocument();
  await userEvent.click(button);
  expect(onRun).toHaveBeenCalledWith("freeze_latent_evidence");
 });

 it("never offers freezing to a wallet that cannot write", () => {
  render(<LatentStage set={{ ...base, requirements_met: true, distinct_category_count: 3, distinct_host_count: 2 }} locked onRun={vi.fn()} />);
  expect(screen.getByRole("button", { name: "Freeze latent evidence" })).toBeDisabled();
 });

 it("offers adjudication only after the set is frozen and the candidate is LATENT", async () => {
  const onRun = show({ frozen: true, candidate_status: "LATENT", evidence_count: 3, distinct_category_count: 3, distinct_host_count: 2, requirements_met: true });
  expect(screen.queryByRole("button", { name: "Freeze latent evidence" })).not.toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: "Evaluate latent value" }));
  expect(onRun).toHaveBeenCalledWith("evaluate_latent_value");
 });

 it("offers nothing further once adjudication has moved the candidate on", () => {
  show({ frozen: true, candidate_status: "WATCHING", requirements_met: true });
  expect(screen.queryByRole("button", { name: "Freeze latent evidence" })).not.toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Evaluate latent value" })).not.toBeInTheDocument();
 });

 it("converts a calendar date to whole UTC seconds", () => {
  expect(toEpoch("2025-01-01")).toBe(1735689600);
  expect(toEpoch("2026-08-01")).toBe(1785542400);
  expect(toEpoch("2026-08-01")).toBeGreaterThan(toEpoch("2025-01-01"));
 });
});
