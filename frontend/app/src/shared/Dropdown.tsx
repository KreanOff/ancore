import {
  type ButtonHTMLAttributes,
  type ReactNode,
  useId,
  useLayoutEffect,
  useRef,
  useState,
} from 'react';

export function Dropdown({
  label,
  trigger,
  children,
  className = '',
  menuClass = '',
  onOpen,
  role = 'menu',
  layer = true,
  triggerClassName = 'tasks-filter-button',
  searchable = true,
  disabled = false,
  triggerProps,
}: {
  label: string;
  trigger: ReactNode;
  children: ReactNode | ((close: () => void) => ReactNode);
  className?: string;
  menuClass?: string;
  role?: 'menu' | 'dialog' | 'group';
  onOpen?: () => void;
  layer?: boolean;
  triggerClassName?: string;
  searchable?: boolean;
  disabled?: boolean;
  triggerProps?: Pick<
    ButtonHTMLAttributes<HTMLButtonElement>,
    'id' | 'aria-describedby' | 'aria-invalid'
  >;
}) {
  const [open, setOpen] = useState(false);
  const anchor = useRef<HTMLButtonElement>(null);
  const menu = useRef<HTMLDivElement>(null);
  const id = useId();
  useLayoutEffect(() => {
    const element = menu.current;
    if (!element || !anchor.current || !open) return;
    if (!layer) {
      const outside = (event: Event) => {
        if (!element.parentElement?.contains(event.target as Node)) setOpen(false);
      };
      const escape = (event: KeyboardEvent) => {
        if (event.key === 'Escape' && !element.querySelector('.ancore-custom-select.is-open')) {
          setOpen(false);
          anchor.current?.focus();
        }
      };
      document.addEventListener('pointerdown', outside, true);
      document.addEventListener('keydown', escape);
      return () => {
        document.removeEventListener('pointerdown', outside, true);
        document.removeEventListener('keydown', escape);
      };
    }
    window.AncoreDropdownLayer?.open(element, anchor.current, () => setOpen(false));
    return () => window.AncoreDropdownLayer?.hide(element);
  }, [open, layer]);
  return (
    <div className={`tasks-filter-dropdown ${className} ${open ? 'is-open' : ''}`}>
      <button
        ref={anchor}
        type="button"
        disabled={disabled}
        className={triggerClassName}
        aria-label={label}
        aria-haspopup={role === 'group' ? 'menu' : role}
        aria-expanded={open}
        aria-controls={id}
        {...triggerProps}
        onClick={() => {
          if (!open) onOpen?.();
          setOpen(!open);
        }}
        onKeyDown={(event) => {
          if (event.defaultPrevented) return;
          if ((event.target as HTMLElement).closest('.ancore-custom-select')) return;
          if (event.key === 'ArrowDown') {
            event.preventDefault();
            if (!open) onOpen?.();
            setOpen(true);
            requestAnimationFrame(() =>
              menu.current?.querySelector<HTMLElement>('button:not(:disabled), a[href]')?.focus(),
            );
          }
        }}
      >
        {trigger}
      </button>
      <div
        ref={menu}
        id={id}
        hidden={!open}
        data-dropdown-search-disabled={!searchable ? '' : undefined}
        className={`tasks-filter-menu ${menuClass}`}
        role={role}
        aria-label={label}
        onKeyDown={(event) => {
          if (event.defaultPrevented) return;
          if ((event.target as HTMLElement).closest('.ancore-custom-select')) return;
          if (
            !['ArrowDown', 'ArrowUp', 'Home', 'End'].includes(event.key) ||
            (event.target as HTMLElement).matches('input')
          )
            return;
          const items = [
            ...event.currentTarget.querySelectorAll<HTMLElement>('button:not(:disabled), a[href]'),
          ].filter((item) => item.getClientRects().length);
          event.preventDefault();
          const index = items.indexOf(document.activeElement as HTMLElement);
          items[
            event.key === 'Home'
              ? 0
              : event.key === 'End'
                ? items.length - 1
                : (index + (event.key === 'ArrowDown' ? 1 : -1) + items.length) % items.length
          ]?.focus();
        }}
      >
        {typeof children === 'function'
          ? children(() => {
              setOpen(false);
              anchor.current?.focus();
            })
          : children}
      </div>
    </div>
  );
}
