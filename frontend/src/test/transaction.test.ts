import { beforeEach, describe, expect, it, vi } from "vitest";

const write=vi.fn(); const wait=vi.fn();
vi.mock("genlayer-js",()=>({createClient:()=>({writeContract:write,waitForTransactionReceipt:wait,connect:vi.fn()})}));
vi.mock("genlayer-js/chains",()=>({studionet:{id:61999,name:"StudioNet",rpcUrls:{default:{http:["https://studio.genlayer.com/api"]}},nativeCurrency:{name:"GEN",symbol:"GEN",decimals:18}}}));

describe("transaction lifecycle",()=>{
 beforeEach(()=>{write.mockReset();wait.mockReset();});
 it("does not report success at submission and waits for FINALIZED",async()=>{vi.stubEnv("VITE_SEEDLING_CONTRACT_ADDRESS","0x1111111111111111111111111111111111111111");vi.resetModules();write.mockResolvedValue("0xhash");wait.mockResolvedValue({status:"FINALIZED"});const {writeContract}=await import("../lib/contract");const phases:string[]=[];await writeContract("0x2222222222222222222222222222222222222222",{request:vi.fn()},"freeze_latent_evidence",["1"],s=>phases.push(s.phase));expect(phases).toEqual(["submitting","submitted","consensus","finalized"]);expect(wait).toHaveBeenCalledWith(expect.objectContaining({status:"FINALIZED"}));});
 it("maps wallet rejection to rejected rather than success",async()=>{vi.stubEnv("VITE_SEEDLING_CONTRACT_ADDRESS","0x1111111111111111111111111111111111111111");vi.resetModules();write.mockRejectedValue(new Error("User rejected request"));const {writeContract}=await import("../lib/contract");const phases:string[]=[];await expect(writeContract("0x2222222222222222222222222222222222222222",{request:vi.fn()},"pause",[],s=>phases.push(s.phase))).rejects.toThrow("rejected");expect(phases.at(-1)).toBe("rejected");});
});
