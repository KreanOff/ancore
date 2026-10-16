import { useEffect, useRef } from 'react';
import { navigate } from './page';
export function useDirtyGuard(dirty: boolean, pending = false) {
  const latest = useRef({ dirty, pending }),
    allowNextNavigation = useRef(false);
  latest.current = { dirty, pending };
  useEffect(() => {
    function beforeNavigate(event: Event) {
      if (allowNextNavigation.current) {
        allowNextNavigation.current = false;
        return;
      }
      if (!latest.current.dirty && !latest.current.pending) return;
      event.preventDefault();
      if (latest.current.pending) return;
      const url = (event as CustomEvent<{ url?: string }>).detail?.url;
      window.showConfirmModal({
        title: 'Niezapisane zmiany',
        message: 'Opuścić stronę bez zapisania zmian?',
        confirmText: 'Opuść bez zapisu',
        cancelText: 'Wróć do edycji',
        onConfirm: () => {
          if (!url) return;
          allowNextNavigation.current = true;
          try {
            void navigate(url);
          } finally {
            // The navigation event consumes permission synchronously. Also
            // clear it when another guard or an invalid target stops the attempt.
            allowNextNavigation.current = false;
          }
        },
      });
    }
    function beforeUnload(event: BeforeUnloadEvent) {
      if (latest.current.dirty || latest.current.pending) {
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
    allowNextNavigation.current = true;
  };
}
