import { useEffect, useRef } from 'react';

// Reveal each widget once, including widgets below the scroll container's fold.
// The content and final chart values remain available without this enhancement.
export function useSummaryMotion() {
  const root = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const element = root.current;
    if (!element) return;
    const preference = window.matchMedia('(prefers-reduced-motion: reduce)');
    let observer: IntersectionObserver | undefined;
    let children: MutationObserver | undefined;
    const observed = new Set<Element>();
    const observe = (panel: Element) => {
      if (observed.has(panel)) return;
      observed.add(panel);
      observer?.observe(panel);
    };
    const update = () => {
      observer?.disconnect();
      children?.disconnect();
      observer = undefined;
      children = undefined;
      observed.clear();
      delete element.dataset.summaryMotion;
      if (preference.matches || !('IntersectionObserver' in window)) return;
      element.dataset.summaryMotion = 'ready';
      observer = new IntersectionObserver(
        (entries) => {
          for (const entry of entries) {
            if (!entry.isIntersecting) continue;
            entry.target.classList.add('is-visible');
            observer?.unobserve(entry.target);
          }
        },
        { threshold: 0.12 },
      );
      element.querySelectorAll('[data-summary-reveal]').forEach(observe);
      if ('MutationObserver' in window) {
        children = new MutationObserver((records) => {
          if (!observer) return;
          for (const panel of observed) {
            if (!element.contains(panel)) {
              observer.unobserve(panel);
              observed.delete(panel);
            }
          }
          for (const record of records) {
            for (const node of record.addedNodes) {
              if (node.nodeType !== 1 || !element.contains(node)) continue;
              const added = node as Element;
              if (added.matches('[data-summary-reveal]')) observe(added);
              added.querySelectorAll('[data-summary-reveal]').forEach(observe);
            }
          }
        });
        children.observe(element, { childList: true, subtree: true });
      }
    };
    update();
    preference.addEventListener('change', update);
    return () => {
      observer?.disconnect();
      children?.disconnect();
      observer = undefined;
      observed.clear();
      preference.removeEventListener('change', update);
      delete element.dataset.summaryMotion;
    };
  }, []);
  return root;
}
