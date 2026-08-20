import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { LoadState, Shell } from "../components/UI";
import { WalletProvider } from "../context/WalletContext";

describe("empty, wallet, and network states",()=>{
 it("shows the polished empty state without fake records",()=>{render(<MemoryRouter><LoadState loading={false} empty><span>hidden</span></LoadState></MemoryRouter>);expect(screen.getByText("No candidates discovered yet")).toBeInTheDocument();expect(screen.queryByText("hidden")).not.toBeInTheDocument();});
 it("shows loading and RPC failure accessibly",()=>{const {rerender}=render(<MemoryRouter><LoadState loading><span/></LoadState></MemoryRouter>);expect(screen.getByRole("status")).toHaveTextContent("Reading finalized contract state");rerender(<MemoryRouter><LoadState loading={false} error="RPC offline"><span/></LoadState></MemoryRouter>);expect(screen.getByRole("alert")).toHaveTextContent("RPC offline");});
 it("tells the visitor when no browser wallet is installed",async()=>{delete (window as {ethereum?:unknown}).ethereum;render(<MemoryRouter><WalletProvider><Shell><p>content</p></Shell></WalletProvider></MemoryRouter>);await userEvent.click(screen.getByRole("button",{name:"Connect wallet"}));expect(await screen.findByRole("alert")).toHaveTextContent("No compatible browser wallet was found.");});
 it("lets each protocol view supply its own empty copy",()=>{render(<MemoryRouter><LoadState loading={false} empty emptyTitle="No appeals filed" emptyBody="Verdicts stay contestable." emptyAction={null}><span>hidden</span></LoadState></MemoryRouter>);expect(screen.getByText("No appeals filed")).toBeInTheDocument();expect(screen.queryByText("No candidates discovered yet")).not.toBeInTheDocument();expect(screen.queryByRole("link",{name:"Register the first candidate"})).not.toBeInTheDocument();});
 it("surfaces wrong-network state after wallet connection",async()=>{const request=vi.fn(async({method}:{method:string})=>method==="eth_requestAccounts"?["0x1111111111111111111111111111111111111111"]:"0x1");Object.assign(window,{ethereum:{request}});render(<MemoryRouter><WalletProvider><Shell><p>content</p></Shell></WalletProvider></MemoryRouter>);await userEvent.click(screen.getByRole("button",{name:"Connect wallet"}));expect(await screen.findByRole("alert")).toHaveTextContent("Wrong network");});
});
