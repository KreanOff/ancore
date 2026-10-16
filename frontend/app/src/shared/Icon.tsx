import { useLayoutEffect, useRef } from 'react';

// The shared icon renderer owns only this empty span; React owns its container.
export function Icon({ name, className }: { name: string; className?: string }) {
  const ref = useRef<HTMLSpanElement>(null);
  useLayoutEffect(() => {
    const host = ref.current;
    const icon = window.AncoreIcons?.create(name, { className });
    if (host && icon) {
      host.replaceChildren(icon);
      window.AncoreIcons?.render(host);
    }
  }, [name, className]);
  return <span className="react-icon" ref={ref} aria-hidden="true" />;
}
