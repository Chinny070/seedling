import { useCallback, useEffect, useState } from "react";
import { readContract, type ContractArg, type ViewMethod } from "../lib/contract";

export function useContractRead<T>(method:ViewMethod,args:ContractArg[]=[]){
  const key=JSON.stringify(args); const [data,setData]=useState<T>(); const [loading,setLoading]=useState(true); const [error,setError]=useState<string>();
  const refresh=useCallback(async()=>{ setLoading(true); setError(undefined); try{setData(await readContract<T>(method,args));}catch(e){setError(e instanceof Error?e.message:"Contract read failed.");}finally{setLoading(false);} },[method,key]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(()=>{void refresh();},[refresh]); return {data,loading,error,refresh};
}
