import { useLayoutEffect, useRef } from 'react';

// Keep the SVG in the template's position so direct-child CSS still applies.
// The shared renderer supplies the glyph; React owns the SVG and its lifecycle.
export function Icon({ name, className }: { name: string; className?: string }) {
  const ref = useRef<SVGSVGElement>(null);
  useLayoutEffect(() => {
    const host = ref.current;
    const icon = window.AncoreIcons?.create(name);
    if (host && icon) {
      const container = document.createElement('span');
      container.append(icon);
      window.AncoreIcons?.render(container);
      const svg = container.querySelector('svg');
      if (!svg) return;
      for (const attribute of svg.attributes) {
        if (attribute.name !== 'class') host.setAttribute(attribute.name, attribute.value);
      }
      host.replaceChildren(...svg.childNodes);
    }
  }, [name]);
  return <svg className={`ancore-icon ${className || ''}`} ref={ref} aria-hidden="true" />;
}
