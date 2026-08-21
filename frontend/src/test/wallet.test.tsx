import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { Shell } from "../components/UI";
import { WalletProvider } from "../context/WalletContext";

const ACCOUNT_A = "0x1111111111111111111111111111111111111111";
const ACCOUNT_B = "0x2222222222222222222222222222222222222222";

let handlers: Record<string, (value: unknown) => void> = {};

function installWallet(chainId = "0xf22f") {
 handlers = {};
 const request = vi.fn(async ({ method }: { method: string }) => method === "eth_requestAccounts" ? [ACCOUNT_A] : chainId);
 Object.assign(window, { ethereum: {
  request,
  on: (event: string, fn: (value: unknown) => void) => { handlers[event] = fn; },
  removeListener: (event: string) => { delete handlers[event]; },
 }});
}

const connect = async () => {
 render(<MemoryRouter><WalletProvider><Shell><p>content</p></Shell></WalletProvider></MemoryRouter>);
 await userEvent.click(screen.getByRole("button", { name: "Connect wallet" }));
};

describe("wallet stays in sync with the injected provider", () => {
 beforeEach(() => { installWallet(); });

 it("follows an account switch made in the wallet", async () => {
  await connect();
  expect(await screen.findByRole("button", { name: "0x1111…1111" })).toBeInTheDocument();
  act(() => handlers.accountsChanged([ACCOUNT_B]));
  expect(screen.getByRole("button", { name: "0x2222…2222" })).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "0x1111…1111" })).not.toBeInTheDocument();
 });

 it("returns to a disconnected state when the wallet revokes all accounts", async () => {
  await connect();
  expect(await screen.findByRole("button", { name: "0x1111…1111" })).toBeInTheDocument();
  act(() => handlers.accountsChanged([]));
  expect(screen.getByRole("button", { name: "Connect wallet" })).toBeInTheDocument();
 });

 it("detects a network switch made after connecting", async () => {
  await connect();
  expect(await screen.findByRole("button", { name: "0x1111…1111" })).toBeInTheDocument();
  expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  act(() => handlers.chainChanged("0x1"));
  expect(screen.getByRole("alert")).toHaveTextContent("Wrong network");
  act(() => handlers.chainChanged("0xf22f"));
  expect(screen.queryByRole("alert")).not.toBeInTheDocument();
 });
});
