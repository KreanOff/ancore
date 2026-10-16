import { useEffect, useRef } from 'react';
import { navigate } from './page';
export function useDirtyGuard(dirty: boolean, pending = false) {
  const latest = useRef({ dirty, pending }),
    discard = useRef(false);
  latest.current = { dirty, pending };
  useEffect(() => {
    function beforeNavigate(event: Event) {
      if (discard.current || (!latest.current.dirty && !latest.current.pending)) return;
      event.preventDefault();
      if (latest.current.pending) return;
      const url = (event as CustomEvent<{ url?: string }>).detail?.url;
      window.showConfirmModal({
        title: 'Niezapisane zmiany',
        message: 'Opuścić stronę bez zapisania zmian?',
        confirmText: 'Opuść bez zapisu',
        cancelText: 'Wróć do edycji',
        onConfirm: () => {
          discard.current = true;
          if (url) navigate(url);
        },
      });
    }
    function beforeUnload(event: BeforeUnloadEvent) {
      if (!discard.current && (latest.current.dirty || latest.current.pending)) {
        event.preventDefault();
        event.returnValue = '';
      }
    }
    document.addEventListener('ancore:before-navigate', beforeNavigate);
    window.addEventListener('beforeunload', beforeUnload);
    return () => {
      document.removeEventListener('ancore:before-navigate', beforeNavigate);
      window.removeEventListener('beforeunload', beforeUnload);
    };
  }, []);
  return () => {
    discard.current = true;
  };
}
