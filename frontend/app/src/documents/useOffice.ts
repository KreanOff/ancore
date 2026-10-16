import { useEffect, useRef, useState } from 'react';
import { documentRequest } from './requests';
import type { SuiteData } from './types';
interface OfficeEditor {
  destroyEditor(): void;
}
declare global {
  interface Window {
    DocsAPI?: { DocEditor: new (id: string, config: Record<string, unknown>) => OfficeEditor };
  }
}
export function useOffice(data: SuiteData, token: string) {
  const [status, setStatus] = useState('Otwieranie edytora…'),
    [error, setError] = useState(''),
    [retry, setRetry] = useState(false),
    [dirty, setDirty] = useState(false);
  const frame = useRef<HTMLIFrameElement>(null),
    holder = useRef<HTMLDivElement>(null),
    persist = useRef<() => void>(() => {});
  useEffect(() => {
    const life = new AbortController(),
      timeouts = new Set<ReturnType<typeof setTimeout>>();
    let interval: ReturnType<typeof setInterval> | undefined,
      editor: OfficeEditor | undefined,
      script: HTMLScriptElement | undefined;
    const delay = (action: () => void, time: number) => {
      const id = setTimeout(() => {
        timeouts.delete(id);
        if (!life.signal.aborted) action();
      }, time);
      timeouts.add(id);
      return id;
    };
    function fail(message: string, canRetry = false) {
      if (!life.signal.aborted) {
        setError(message);
        setRetry(canRetry);
      }
    }
    function clear() {
      setError('');
      setRetry(false);
    }
    if (data.board_url) {
      let ready = false;
      const message = (event: MessageEvent) => {
        if (
          event.origin !== location.origin ||
          event.source !== frame.current?.contentWindow ||
          event.data?.source !== 'ancore-board'
        )
          return;
        const value = event.data;
        if (
          value.type === 'status' &&
          typeof value.message === 'string' &&
          typeof value.dirty === 'boolean'
        ) {
          setStatus(value.message);
          setDirty(value.dirty);
          ready = true;
          if (!value.dirty) clear();
        } else if (value.type === 'error' && typeof value.message === 'string') {
          fail(value.message, true);
          if (typeof value.dirty === 'boolean') setDirty(value.dirty);
          ready = true;
        }
      };
      window.addEventListener('message', message);
      persist.current = () => {
        if (ready)
          frame.current?.contentWindow?.postMessage(
            { source: 'ancore', type: 'save' },
            location.origin,
          );
      };
      delay(() => {
        if (!ready) fail('Nie udało się załadować tablicy. Odśwież stronę i sprawdź połączenie.');
      }, 20000);
      return () => {
        life.abort();
        window.removeEventListener('message', message);
        timeouts.forEach(clearTimeout);
      };
    }
    if (!data.editor_config) {
      setStatus('Dokument zapisany');
      return () => life.abort();
    }
    const config = { ...data.editor_config };
    let revision = data.revision,
      pending = false,
      sessionInvalid = false,
      generation = 0,
      savingGeneration = 0,
      attempt = 0,
      autoSave: ReturnType<typeof setTimeout> | undefined;
    async function poll() {
      try {
        const state = await documentRequest<{
          key: string;
          revision: number;
          save_error: boolean;
          saved_at: string;
        }>(data.state_url, token, life.signal);
        if (life.signal.aborted) return;
        if (state.key !== config.document.key) {
          sessionInvalid = true;
          pending = false;
          setStatus('Sesja dokumentu zmieniła się');
          fail(
            'Plik został podmieniony lub sesja zakończona. Pobierz swoje zmiany z menu Plik edytora i otwórz aktualną wersję w nowej karcie.',
          );
          return;
        }
        if (state.save_error)
          fail(
            'Nie udało się zapisać pliku w Ancore. Pozostaw edytor otwarty i spróbuj zapisać ponownie.',
            true,
          );
        if (state.revision > revision) {
          revision = state.revision;
          pending = false;
          clear();
          setStatus(
            savingGeneration === generation
              ? `Zapisano w Ancore ${state.saved_at}`
              : 'Nowsze zmiany w edytorze',
          );
        }
      } catch {
        if (pending) fail('Brak potwierdzenia zapisu. Sprawdź połączenie i ponów zapis.', true);
      }
    }
    async function save() {
      if (pending || sessionInvalid || life.signal.aborted) return;
      pending = true;
      const current = ++attempt;
      savingGeneration = generation;
      setStatus('Zapisywanie w Ancore…');
      clear();
      try {
        const result = await documentRequest<{ pending: boolean }>(
          data.save_url,
          token,
          life.signal,
          new FormData(),
          { 'X-Office-Key': config.document.key },
        );
        if (life.signal.aborted) return;
        if (!result.pending) {
          pending = false;
          setStatus('Brak nowych zmian do zapisania');
        } else
          delay(() => {
            if (pending && attempt === current) {
              pending = false;
              fail(
                'Zapis nie został jeszcze potwierdzony. Spróbuj ponownie; dokument pozostaje w edytorze.',
                true,
              );
            }
          }, 30000);
        await poll();
      } catch (reason) {
        pending = false;
        fail(
          reason instanceof Error ? reason.message : 'Nie udało się zapisać. Spróbuj ponownie.',
          true,
        );
      }
    }
    persist.current = () => void save();
    config.events = {
      onAppReady() {
        if (!life.signal.aborted) setStatus('Ładowanie dokumentu…');
      },
      onDocumentReady() {
        if (life.signal.aborted) return;
        setStatus('Dokument otwarty');
        clearInterval(interval);
        interval = setInterval(() => void poll(), 4000);
      },
      onDocumentStateChange(event: { data: boolean }) {
        if (life.signal.aborted) return;
        if (event.data) {
          generation++;
          setStatus('Zmiany w edytorze');
        } else {
          clearTimeout(autoSave);
          autoSave = delay(() => void save(), 1500);
        }
      },
      onError() {
        fail('Edytor zgłosił błąd. Zachowaj otwarte okno i sprawdź połączenie z serwerem edycji.');
      },
      onRequestClose() {
        if (!life.signal.aborted) location.href = data.back_url;
      },
    };
    function start() {
      if (life.signal.aborted) return;
      try {
        if (!window.DocsAPI) throw new Error();
        editor = new window.DocsAPI.DocEditor('office-doc-editor', config);
      } catch {
        fail('Nie udało się uruchomić edytora. Odśwież stronę.');
      }
    }
    if (window.DocsAPI) start();
    else {
      script = document.createElement('script');
      script.src = data.api_url;
      script.onload = start;
      script.onerror = () => {
        if (!life.signal.aborted) {
          setStatus('Edytor niedostępny');
          fail(
            'Nie można połączyć się z serwerem edycji. Uruchom go i odśwież stronę. Plik pozostaje zapisany w Ancore.',
          );
        }
      };
      document.head.append(script);
    }
    const dispose = () => {
      life.abort();
      clearInterval(interval);
      clearTimeout(autoSave);
      timeouts.forEach(clearTimeout);
      if (script) {
        script.onload = script.onerror = null;
        script.remove();
      }
      editor?.destroyEditor();
      editor = undefined;
    };
    window.addEventListener('pagehide', dispose, { once: true });
    return () => {
      window.removeEventListener('pagehide', dispose);
      dispose();
    };
  }, [data, token]);
  return { status, error, retry, dirty, frame, holder, save: () => persist.current() };
}
