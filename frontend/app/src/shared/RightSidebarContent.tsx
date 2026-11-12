import type { ReactNode } from 'react';
import { createPortal } from 'react-dom';

export function openRightSidebar() {
  document
    .querySelector<HTMLButtonElement>('[data-right-sidebar-toggle][aria-expanded="false"]')
    ?.click();
}

// The host lives outside both React roots, so initial shell mounting cannot replace it.
export function RightSidebarContent({ children }: { children: ReactNode }) {
  const host =
    typeof document === 'undefined' ? null : document.getElementById('app-right-sidebar-content');
  return host ? createPortal(children, host) : children;
}
