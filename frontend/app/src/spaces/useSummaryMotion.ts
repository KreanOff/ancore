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
    const update = () => {
      observer?.disconnect();
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
      element.querySelectorAll('[data-summary-reveal]').forEach((panel) => {
        observer?.observe(panel);
      });
    };
    update();
    preference.addEventListener('change', update);
    return () => {
      observer?.disconnect();
      preference.removeEventListener('change', update);
      delete element.dataset.summaryMotion;
    };
  }, []);
  return root;
}
