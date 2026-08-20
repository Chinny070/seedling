import { createContext, useContext, useState, type ReactNode } from "react";
import { makeClient, NETWORK, type HexAddress, type TxState } from "../lib/contract";

type Provider = { request(args:{method:string;params?:unknown[]}):Promise<unknown>; on?(event:string, fn:(value:unknown)=>void):void };
interface WalletValue { account?:HexAddress; provider?:Provider; connecting:boolean; wrongNetwork:boolean; error?:string; tx:TxState; setTx(value:TxState):void; connect():Promise<void>; switchNetwork():Promise<void> }
const WalletContext = createContext<WalletValue | null>(null);

export function WalletProvider({children}:{children:ReactNode}) {
  const [account,setAccount]=useState<HexAddress>(); const [provider,setProvider]=useState<Provider>();
  const [connecting,setConnecting]=useState(false); const [wrongNetwork,setWrongNetwork]=useState(false);
  const [error,setError]=useState<string>(); const [tx,setTx]=useState<TxState>({phase:"idle"});
  async function connect(){
    setConnecting(true); setError(undefined);
    try {
      const injected=(window as typeof window & {ethereum?:Provider}).ethereum;
      if(!injected) throw new Error("No compatible browser wallet was found.");
      const accounts=await injected.request({method:"eth_requestAccounts"}) as HexAddress[];
      const chain=await injected.request({method:"eth_chainId"}) as string;
      setProvider(injected); setAccount(accounts[0]); setWrongNetwork(parseInt(chain,16)!==NETWORK.id);
    } catch(e){ setError(e instanceof Error?e.message:"Wallet connection failed."); }
    finally { setConnecting(false); }
  }
  async function switchNetwork(){
    if(!provider||!account) return;
    try { await makeClient(account,provider).connect("studionet"); setWrongNetwork(false); }
    catch(e){ setError(e instanceof Error?e.message:"Network switch failed."); }
  }
  const value={account,provider,connecting,wrongNetwork,error,tx,setTx,connect,switchNetwork};
  return <WalletContext.Provider value={value}>{children}</WalletContext.Provider>;
}
// eslint-disable-next-line react-refresh/only-export-components
export function useWallet(){ const value=useContext(WalletContext); if(!value) throw new Error("WalletProvider missing"); return value; }
