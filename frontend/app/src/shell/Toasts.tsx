import { useEffect, useRef, useState } from 'react';
import { createPortal, flushSync } from 'react-dom';
import type { ToastMessage } from './navigation-types';
interface Toast extends ToastMessage {
  id: number;
  hiding?: boolean;
  key?: string;
}
export default function Toasts({ initial }: { initial: ToastMessage[] }) {
  const [items, setItems] = useState<Toast[]>([]);
  const count = useRef(0);
  useEffect(() => {
    const timers = new Set<ReturnType<typeof setTimeout>>();
    const later = (fn: () => void, ms: number) => {
      const timer = setTimeout(() => {
        timers.delete(timer);
        fn();
      }, ms);
      timers.add(timer);
    };
    const hide = (element: HTMLElement | null | undefined) => {
      const id = Number(element?.dataset.toastId);
      setItems((previous) =>
        previous.map((item) => (item.id === id ? { ...item, hiding: true } : item)),
      );
      later(() => setItems((previous) => previous.filter((item) => item.id !== id)), 300);
    };
    const show = (
      message: string,
      type = 'info',
      options: { duration?: number; dedupeKey?: string } = {},
    ) => {
      if (!message) return null;
      const id = ++count.current;
      flushSync(() =>
        setItems((previous) => [
          ...previous.filter((item) => !options.dedupeKey || item.key !== options.dedupeKey),
          { id, message, type, key: options.dedupeKey },
        ]),
      );
      const element = document.querySelector<HTMLElement>(`[data-toast-id="${id}"]`);
      const duration = Number.isFinite(options.duration) ? options.duration! : 5000;
      if (duration > 0) later(() => hide(element), duration);
      return element;
    };
    window.showNotification = show;
    window.hideNotification = window.closeNotification = hide;
    // Schedule outside the effect commit because the compatibility API returns a DOM handle.
    later(() => initial.forEach((item) => show(item.message, item.type)), 0);
    const incoming = (event: Event) =>
      (event as CustomEvent<ToastMessage[]>).detail.forEach((item) =>
        show(item.message, item.type),
      );
    document.addEventListener('ancore:messages', incoming);
    return () => {
      timers.forEach(clearTimeout);
      document.removeEventListener('ancore:messages', incoming);
      if (window.showNotification === show) {
        delete window.showNotification;
        delete window.hideNotification;
        delete window.closeNotification;
      }
    };
  }, [initial]);
  return createPortal(
    items.length ? (
      <div className="notifications-container">
        {items.map((item) => (
          <div
            key={item.id}
            data-toast-id={item.id}
            data-notification-key={item.key}
            className={`notification ${item.type}${item.hiding ? ' hiding' : ''}`}
            role={item.type === 'error' ? 'alert' : 'status'}
            aria-live={item.type === 'error' ? 'assertive' : 'polite'}
          >
            {item.message}
          </div>
        ))}
      </div>
    ) : null,
    document.getElementById('app-notifications')!,
  );
}
