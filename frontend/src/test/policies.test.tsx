import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

const reads = vi.hoisted(() => ({
  obs: { items: [] as unknown[], total: 0 },
  fund: { items: [] as unknown[], total: 0 },
}));

vi.mock("../hooks/useContract", () => ({
  useContractRead: (method: string) => ({
    data: method === "list_observation_policies" ? reads.obs : reads.fund,
    loading: false,
    error: undefined,
    refresh: vi.fn(),
  }),
}));

import { WalletProvider } from "../context/WalletContext";
import { Register } from "../pages/Pages";

const activeObs = { policy_id: "1", family_id: "1", version: 1, creator: "0x1", name: "Baseline observation", candidate_types: ["DATASET"], minimum_evidence_categories: 3, minimum_independent_sources: 2, checkpoint_interval: 2592000, status: "ACTIVE" };
const activeFund = { funding_policy_id: "1", family_id: "1", version: 1, creator: "0x1", name: "Progressive recognition", latent_cap_bps: 500, watching_cap_bps: 1500, emerging_cap_bps: 3500, material_cap_bps: 6500, systemic_cap_bps: 10000, minimum_public_value_bps: 6000, maximum_gaming_risk_bps: 3000, minimum_attribution_confidence_bps: 6000, status: "ACTIVE" };

const renderRegister = () => render(<MemoryRouter><WalletProvider><Register/></WalletProvider></MemoryRouter>);

describe("policy binding gates candidate registration", () => {
 beforeEach(() => { reads.obs = { items: [], total: 0 }; reads.fund = { items: [], total: 0 }; });

 it("blocks registration and explains why when no active policies exist", () => {
  renderRegister();
  expect(screen.getByText("No active policies exist yet.")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Create the first policies" })).toHaveAttribute("href", "/policies");
  expect(screen.getByRole("button", { name: "Submit registration" })).toBeDisabled();
  expect(screen.queryByRole("combobox", { name: /Observation policy/ })).not.toBeInTheDocument();
 });

 it("offers only ACTIVE policy versions once they exist on-chain", () => {
  reads.obs = { items: [activeObs, { ...activeObs, policy_id: "2", name: "Superseded observation", status: "INACTIVE" }], total: 2 };
  reads.fund = { items: [activeFund], total: 1 };
  renderRegister();
  expect(screen.queryByText("No active policies exist yet.")).not.toBeInTheDocument();
  expect(screen.getByRole("option", { name: "#1 — Baseline observation (v1)" })).toBeInTheDocument();
  expect(screen.queryByRole("option", { name: /Superseded observation/ })).not.toBeInTheDocument();
  expect(screen.getByRole("option", { name: "#1 — Progressive recognition (v1)" })).toBeInTheDocument();
 });

 it("still blocks when only one side of the binding is active", () => {
  reads.obs = { items: [activeObs], total: 1 };
  reads.fund = { items: [{ ...activeFund, status: "INACTIVE" }], total: 1 };
  renderRegister();
  expect(screen.getByText("No active policies exist yet.")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Submit registration" })).toBeDisabled();
 });
});
