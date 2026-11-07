import { forwardRef, type HTMLAttributes } from 'react';

export const PageTabs = forwardRef<HTMLElement, HTMLAttributes<HTMLElement> & { label: string }>(
  function PageTabs({ label, children, className = '', ...props }, ref) {
    return (
      <nav
        {...props}
        ref={ref}
        className={`notifications-tabs work-tabs app-page-tabs ${className}`}
        aria-label={label}
      >
        {children}
      </nav>
    );
  },
);
