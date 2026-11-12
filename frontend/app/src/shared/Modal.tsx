import { type ReactNode, useEffect, useRef } from 'react';
import { createPortal } from 'react-dom';
import { acquireInert } from './inert';

export function Modal({
  title,
  size = 'panel',
  className = '',
  children,
  footer,
  onClose,
  dirty = false,
  pending = false,
  header,
  dialogClassName = '',
  hostId = 'app-page-modals',
  returnFocus,
  id,
}: {
  title: string;
  size?: 'panel' | 'compact';
  className?: string;
  children: ReactNode;
  footer?: ReactNode;
  onClose: () => void;
  dirty?: boolean;
  pending?: boolean;
  header?: (close: () => void) => ReactNode;
  dialogClassName?: string;
  hostId?: string;
  returnFocus?: HTMLElement | null;
  id?: string;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const latest = useRef({ onClose, dirty, pending });
  latest.current = { onClose, dirty, pending };
  const discard = useRef(false);
  useEffect(() => {
    const element = ref.current!;
    const previous = returnFocus?.isConnected ? returnFocus : document.activeElement;
    const background: HTMLElement[] = [];
    const close = () => window.AncoreTaskModals?.close(element);
    const beforeClose = (event: Event) => {
      if (event.target !== element) return;
      if (latest.current.pending) {
        event.preventDefault();
        return;
      }
      if (latest.current.dirty && !discard.current) {
        event.preventDefault();
        window.showConfirmModal({
          title: 'Niezapisane zmiany',
          message: 'Zamknąć formularz bez zapisania zmian?',
          confirmText: 'Zamknij bez zapisu',
          cancelText: 'Wróć do edycji',
          onConfirm: () => {
            if (element.isConnected) {
              discard.current = true;
              close();
            }
          },
        });
      }
    };
    const closed = (event: Event) => {
      if (event.target === element) latest.current.onClose();
    };
    element.addEventListener('ancore:task-modal-before-close', beforeClose);
    element.addEventListener('ancore:task-modal-closed', closed);
    const ownControls = (selector: string) =>
      [...element.querySelectorAll<HTMLElement>(selector)].find(
        (control) =>
          control.closest('.tasks-modal') === element &&
          !control.closest('[hidden]') &&
          !control.matches(':disabled'),
      );
    window.AncoreTaskModals?.open(
      element,
      ownControls('[role="tab"][aria-selected="true"]') ||
        ownControls('input:not([type="hidden"]), textarea') ||
        ownControls('button'),
      undefined,
      previous instanceof HTMLElement ? previous : undefined,
    );
    for (
      let node: HTMLElement | null = element.parentElement;
      node && node !== document.body;
      node = node.parentElement
    ) {
      [...node.parentElement!.children].forEach((sibling) => {
        if (sibling !== node && sibling instanceof HTMLElement) {
          background.push(sibling);
        }
      });
    }
    const releaseBackground = acquireInert(background);
    const beforeNavigate = (event: Event) => {
      if (latest.current.dirty || latest.current.pending) {
        event.preventDefault();
        close();
      }
    };
    const beforeUnload = (event: BeforeUnloadEvent) => {
      if (latest.current.dirty || latest.current.pending) {
        event.preventDefault();
        event.returnValue = '';
      }
    };
    document.addEventListener('ancore:before-navigate', beforeNavigate);
    window.addEventListener('beforeunload', beforeUnload);
    return () => {
      window.AncoreCustomSelect?.closeAll();
      window.AncoreDropdownLayer?.dismiss();
      element.removeEventListener('ancore:task-modal-before-close', beforeClose);
      element.removeEventListener('ancore:task-modal-closed', closed);
      document.removeEventListener('ancore:before-navigate', beforeNavigate);
      window.removeEventListener('beforeunload', beforeUnload);
      releaseBackground();
      if (!document.querySelector('.tasks-modal.is-open'))
        document.body.classList.remove('modal-open');
      if (previous instanceof HTMLElement && previous.isConnected)
        previous.focus({ preventScroll: true });
    };
  }, []);
  const host = document.getElementById(hostId);
  if (!host) return null;
  return createPortal(
    <div
      ref={ref}
      id={id}
      className={`tasks-modal app-modal-panel tasks-form-modal ${size === 'compact' ? 'app-modal-panel--compact ' : ''}${className}`}
      role="dialog"
      aria-modal="true"
      aria-label={title}
      aria-hidden="true"
      aria-busy={pending}
      onClick={(event) => {
        if (event.target === event.currentTarget)
          window.AncoreTaskModals?.close(event.currentTarget);
      }}
    >
      <div className={`tasks-modal__dialog ${dialogClassName}`}>
        {header ? (
          header(() => window.AncoreTaskModals?.close(ref.current!))
        ) : (
          <header className="tasks-modal__header">
            <h2>{title}</h2>
            <button
              type="button"
              className="tasks-modal__close"
              aria-label="Zamknij"
              disabled={pending}
              onClick={() => window.AncoreTaskModals?.close(ref.current!)}
            />
          </header>
        )}
        {children}
        {footer}
      </div>
    </div>,
    host,
  );
}
