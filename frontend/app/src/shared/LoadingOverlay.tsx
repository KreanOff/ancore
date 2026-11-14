import { useEffect, useRef } from 'react';
import { createPortal } from 'react-dom';
import { acquireInert } from './inert';

export function LoadingOverlay({ active, label }: { active: boolean; label: string }) {
  const overlay = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!active || !overlay.current) return;
    return acquireInert(
      [...document.body.children].filter(
        (element): element is HTMLElement =>
          element instanceof HTMLElement && element !== overlay.current,
      ),
    );
  }, [active]);
  if (!active) return null;
  // Keep the status outside busy forms and transformed modal panels.
  return createPortal(
    <div
      ref={overlay}
      className="app-loading-overlay"
      data-loading-active={active}
      role="status"
      aria-live="polite"
      aria-atomic="true"
      aria-hidden={!active}
    >
      <span className="app-loading-indicator" aria-hidden="true">
        <span />
        <span />
        <span />
        <span />
      </span>
      <span className="u-sr-only">{active ? label : ''}</span>
    </div>,
    document.body,
  );
}
