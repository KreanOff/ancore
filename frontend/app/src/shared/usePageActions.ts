import { useEffect, useRef, useState } from 'react';
import type { FormDialogData } from '../forms/FormDialog';
import { type Page, type PageProps, navigate, pageRequest, setPageLocation } from './page';
import { errorMessage } from './api';
export function usePageActions(
  { initial, csrfToken }: PageProps,
  initialModal: FormDialogData | null = null,
) {
  const [modal, setModal] = useState<FormDialogData | null>(initialModal),
    [busy, setBusy] = useState(false),
    [error, setError] = useState('');
  const life = useRef(new AbortController()),
    pending = useRef(false),
    returnFocus = useRef<HTMLElement | null>(null);
  useEffect(() => () => life.current.abort(), []);
  async function open(url: string) {
    if (pending.current) return;
    // Loading disables the trigger before the dialog mounts, which can blur it.
    returnFocus.current =
      document.activeElement instanceof HTMLElement ? document.activeElement : null;
    pending.current = true;
    setBusy(true);
    setError('');
    try {
      const page = await pageRequest<Page>(initial.api_url, url, csrfToken, life.current.signal);
      const dialog =
        page.type === 'form'
          ? (page.data as FormDialogData)
          : (page.data as { modal?: FormDialogData }).modal;
      if (!dialog) throw new Error('Nie udało się otworzyć formularza.');
      if (!life.current.signal.aborted) setModal(dialog);
    } catch (exception) {
      if (!life.current.signal.aborted) setError(errorMessage(exception));
    } finally {
      pending.current = false;
      setBusy(false);
    }
  }
  async function act(url: string, values: Record<string, string | string[]>) {
    if (pending.current) return;
    pending.current = true;
    setBusy(true);
    setError('');
    const body = new FormData();
    Object.entries(values).forEach(([key, value]) => {
      if (Array.isArray(value)) value.forEach((item) => body.append(key, item));
      else body.set(key, value);
    });
    try {
      const result = await pageRequest<{ redirect?: string; invalidated_return_paths?: string[] }>(
        initial.api_url,
        url,
        csrfToken,
        life.current.signal,
        body,
      );
      if (!life.current.signal.aborted) {
        if (result.invalidated_return_paths)
          window.AncoreApp?.invalidateManagementReturn?.(result.invalidated_return_paths);
        await navigate(result.redirect || initial.url);
      }
    } catch (exception) {
      if (!life.current.signal.aborted) setError(errorMessage(exception));
    } finally {
      pending.current = false;
      setBusy(false);
    }
  }
  return {
    modal,
    returnFocus: returnFocus.current,
    busy,
    error,
    open,
    act,
    close: () => {
      setModal(null);
      if (initialModal) setPageLocation(initialModal.return_url);
    },
  };
}
