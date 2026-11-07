import { useLayoutEffect, useRef, useState } from 'react';
import { errorMessage } from './api';
import { pageRequest, setPageLocation, type Page, type PageProps } from './page';

/** Fetch a larger server window without remounting the page or losing row state. */
export function useLoadMorePage<T>(
  { initial, csrfToken }: PageProps,
  nextUrl: (data: T) => string,
) {
  const [data, setData] = useState(initial.data as T);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const request = useRef<AbortController | null>(null);
  useLayoutEffect(() => {
    setData(initial.data as T);
    setLoading(false);
    setError('');
    return () => {
      request.current?.abort();
      request.current = null;
    };
  }, [initial]);

  async function loadMore() {
    const next = nextUrl(data);
    if (!next || request.current) return;
    const controller = new AbortController();
    request.current = controller;
    setLoading(true);
    setError('');
    try {
      const result = await pageRequest<Page>(initial.api_url, next, csrfToken, controller.signal);
      if (controller.signal.aborted || request.current !== controller) return;
      if (result.type !== initial.type || !result.data || typeof result.data !== 'object')
        throw new Error('Nie udało się wczytać kolejnych wyników.');
      setData(result.data as T);
      setPageLocation(result.url);
    } catch (exception) {
      if (!controller.signal.aborted && request.current === controller)
        setError(errorMessage(exception));
    } finally {
      if (request.current === controller) {
        request.current = null;
        setLoading(false);
      }
    }
  }
  return { data, loading, error, loadMore };
}
