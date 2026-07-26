import { useEffect, useRef } from "react";

// Each view already fetches its own data on mount; this just re-runs
// `reload` when the shared header refresh button increments `signal`,
// skipping the very first render so mount doesn't double-fetch.
export function useRefreshSignal(signal, reload) {
  const isFirstRun = useRef(true);

  useEffect(() => {
    if (isFirstRun.current) {
      isFirstRun.current = false;
      return;
    }
    reload();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [signal]);
}
