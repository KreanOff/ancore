import { type FormEvent, useCallback, useEffect, useRef, useState } from 'react';

// Native POSTs must retain the browser's beforeunload guards and session redirects.
export function useNativeSubmitLoading(fallbackFocus?: () => HTMLElement | null) {
  const [pending, setPending] = useState(false);
  const active = useRef(false);
  const previousFocus = useRef<HTMLElement | null>(null);
  const fallback = useRef(fallbackFocus);
  fallback.current = fallbackFocus;
  const frame = useRef<number>();
  const timer = useRef<number>();
  const reset = useCallback(() => {
    if (!active.current) return;
    active.current = false;
    setPending(false);
    frame.current = requestAnimationFrame(() => {
      const previous = previousFocus.current;
      const target =
        previous?.isConnected && previous.getClientRects().length ? previous : fallback.current?.();
      if (target && !target.closest('[inert]') && !target.matches(':disabled'))
        target.focus({ preventScroll: true });
      previousFocus.current = null;
      frame.current = undefined;
    });
  }, []);
  useEffect(() => {
    const restore = (event: PageTransitionEvent) => {
      if (event.persisted) reset();
    };
    const beforeUnload = (event: BeforeUnloadEvent) => {
      if (!active.current) return;
      // A later editor listener can cancel leaving. Observe the completed event.
      if (timer.current !== undefined) window.clearTimeout(timer.current);
      timer.current = window.setTimeout(() => {
        timer.current = undefined;
        if (event.defaultPrevented) reset();
      }, 0);
    };
    window.addEventListener('pageshow', restore);
    window.addEventListener('beforeunload', beforeUnload);
    return () => {
      window.removeEventListener('pageshow', restore);
      window.removeEventListener('beforeunload', beforeUnload);
      if (frame.current !== undefined) cancelAnimationFrame(frame.current);
      if (timer.current !== undefined) window.clearTimeout(timer.current);
    };
  }, [reset]);
  const start = useCallback(() => {
    if (active.current) return false;
    if (frame.current !== undefined) cancelAnimationFrame(frame.current);
    active.current = true;
    previousFocus.current =
      document.activeElement instanceof HTMLElement ? document.activeElement : null;
    setPending(true);
    return true;
  }, []);
  const onSubmit = useCallback(
    (event: FormEvent<HTMLFormElement>) => {
      if (event.defaultPrevented) return;
      if (!start()) {
        event.preventDefault();
        return;
      }
      const nativeEvent = event.nativeEvent;
      queueMicrotask(() => {
        if (nativeEvent.defaultPrevented) reset();
      });
    },
    [reset, start],
  );
  return { pending, start, reset, onSubmit };
}
