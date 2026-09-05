import { useCallback, useEffect, useRef, useState } from "react";

export function useAsync<T>(fetcher: () => Promise<T>, deps: unknown[] = []) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const generation = useRef(0);

  const run = useCallback(() => {
    const current = ++generation.current;
    setLoading(true);
    setError(null);
    fetcher()
      .then((result) => { if (current === generation.current) setData(result); })
      .catch((err) => { if (current === generation.current) setError(err instanceof Error ? err : new Error(String(err))); })
      .finally(() => { if (current === generation.current) setLoading(false); });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  useEffect(() => {
    run();
    return () => { generation.current += 1; };
  }, [run]);

  return { data, loading, error, refetch: run };
}
