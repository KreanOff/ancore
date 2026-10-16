import { setPageLocation } from '../shared/page';
import { useEffect, useRef, useState } from 'react';
import { flushSync } from 'react-dom';
import { errorMessage } from '../shared/api';
import { type Page, type PageProps, navigate, pageRequest } from '../shared/page';
import { useDirtyGuard } from '../shared/useDirtyGuard';
import type { DocumentModal } from './types';
export function useActions(props: PageProps, initial: DocumentModal | null) {
  const [modal, setModal] = useState(initial),
    [files, setFiles] = useState<File[]>([]),
    [busy, setBusy] = useState(false),
    [error, setError] = useState('');
  const life = useRef(new AbortController()),
    pending = useRef(false);
  useDirtyGuard(false, busy);
  useEffect(() => () => life.current.abort(), []);
  async function open(url: string, upload: File[] = []) {
    if (pending.current) return;
    pending.current = true;
    setBusy(true);
    setError('');
    try {
      const result = await pageRequest<Page>(
        props.initial.api_url,
        url,
        props.csrfToken,
        life.current.signal,
      );
      if (result.type !== 'document-form') throw new Error('Nie udało się otworzyć okna.');
      if (!life.current.signal.aborted) {
        setFiles(upload);
        setModal(result.data as DocumentModal);
      }
    } catch (e) {
      if (!life.current.signal.aborted) setError(errorMessage(e));
    } finally {
      pending.current = false;
      setBusy(false);
    }
  }
  async function act(
    url: string,
    values: Record<string, string>,
    reload?: string,
    beforeNavigate?: () => Promise<void>,
  ) {
    if (pending.current) return;
    pending.current = true;
    setBusy(true);
    setError('');
    const body = new FormData();
    Object.entries(values).forEach(([key, value]) => body.set(key, value));
    try {
      const result = await pageRequest<{ redirect: string }>(
        props.initial.api_url,
        url,
        props.csrfToken,
        life.current.signal,
        body,
      );
      if (!life.current.signal.aborted) {
        await beforeNavigate?.();
        if (life.current.signal.aborted) return;
        flushSync(() => setBusy(false));
        await navigate(reload || result.redirect);
        return true;
      }
    } catch (e) {
      if (!life.current.signal.aborted) setError(errorMessage(e));
    } finally {
      pending.current = false;
      setBusy(false);
    }
    return false;
  }
  function close() {
    setModal(null);
    setFiles([]);
    if (initial) setPageLocation(modal?.return_url || initial.return_url);
  }
  return { modal, files, busy, error, open, act, close };
}
