import { useCallback, useEffect, useRef, useState } from 'react';

// Stored text alone is never permission to render government content.
export default function useGovernmentAccess({getToken, verify, clear}) {
  const [status,setStatus] = useState('checking');
  const mounted = useRef(false), request = useRef(null), expiry = useRef(null);
  const signOut = useCallback(() => {
    request.current?.abort(); clearTimeout(expiry.current); clear();
    if (mounted.current) setStatus('signed_out');
  },[clear]);
  const check = useCallback(async () => {
    request.current?.abort();
    const token = getToken();
    if (!token) {signOut(); return false;}
    const controller = new AbortController(); request.current = controller;
    try {
      const authority = await verify(controller.signal);
      if (controller.signal.aborted || !mounted.current || getToken()!==token) return false;
      if (!authority.authenticated || authority.role!=='government_authority' || !Number.isFinite(authority.expires_at)) throw new Error('Government session required');
      const remaining = authority.expires_at*1000-Date.now();
      if (remaining<=0) {signOut();return false;}
      setStatus('verified');
      clearTimeout(expiry.current);
      expiry.current = setTimeout(signOut,Math.min(remaining,2147483647));
      return true;
    } catch {
      if (!controller.signal.aborted && mounted.current) signOut();
      return false;
    }
  },[getToken,verify,signOut]);
  useEffect(() => {
    mounted.current=true; check();
    const timer=setInterval(check,60000);
    const onFocus=()=>check();
    window.addEventListener('focus',onFocus);
    window.addEventListener('government-unauthorized',signOut);
    return()=>{mounted.current=false;request.current?.abort();clearTimeout(expiry.current);clearInterval(timer);window.removeEventListener('focus',onFocus);window.removeEventListener('government-unauthorized',signOut);};
  },[check,signOut]);
  return {status,check,signOut};
}
