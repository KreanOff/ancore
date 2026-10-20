import { type DragEvent, type PointerEvent, useEffect, useLayoutEffect, useRef } from 'react';
import type { DetailData } from './types';

const itemSelector = '[data-work-motion-item]';
const easing = 'cubic-bezier(0.22, 1, 0.36, 1)';
type Position = { group: string; before: number | null; after: number | null };
type Drag = {
  source: HTMLElement;
  preview: HTMLElement;
  image: HTMLCanvasElement;
  marker: HTMLElement;
  column: HTMLElement | null;
  target: Position | null;
  x: number;
  y: number;
  offsetX: number;
  offsetY: number;
  scale: number;
};

// Own only transient decorations. React owns the task nodes and their order.
export function useItemMotion(data: DetailData, onCancel: () => void) {
  const root = useRef<HTMLDivElement>(null);
  const drag = useRef<Drag | null>(null);
  const positions = useRef<Map<string, DOMRect> | null>(null);
  const parents = useRef(new Map<string, HTMLElement | null>());
  const animations = useRef(new Map<HTMLElement, Animation>());
  const landings = useRef(new Map<HTMLElement, { preview: HTMLElement; animation: Animation }>());
  const frame = useRef(0);
  const startedOnControl = useRef(false);
  const cancel = useRef(onCancel);
  cancel.current = onCancel;
  const reduced = () => window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const nodes = () => [...(root.current?.querySelectorAll<HTMLElement>(itemSelector) || [])];

  function capture() {
    const elements = nodes();
    positions.current = new Map(
      elements.map((node) => [
        node.dataset.workMotionItem!,
        (landings.current.get(node)?.preview || node).getBoundingClientRect(),
      ]),
    );
    parents.current = new Map(
      elements.map((node) => [
        node.dataset.workMotionItem!,
        landings.current.has(node) ? null : node.parentElement,
      ]),
    );
  }
  function clone(source: HTMLElement) {
    const preview = source.cloneNode(true) as HTMLElement;
    preview.classList.add('work-board-drag-preview');
    preview.classList.remove('is-board-arriving', 'is-motion-landing', 'is-dragging');
    preview.removeAttribute('draggable');
    for (const node of [preview, ...preview.querySelectorAll('*')]) {
      for (const attribute of [...node.attributes])
        if (
          attribute.name === 'id' ||
          attribute.name === 'for' ||
          (attribute.name.startsWith('data-') && !attribute.name.startsWith('data-icon')) ||
          ['aria-controls', 'aria-labelledby', 'popovertarget', 'tabindex'].includes(attribute.name)
        )
          node.removeAttribute(attribute.name);
    }
    preview.inert = true;
    preview.setAttribute('aria-hidden', 'true');
    preview.style.width = `${source.offsetWidth}px`;
    preview.style.height = `${source.offsetHeight}px`;
    return preview;
  }
  function clearLandings() {
    landings.current.forEach(({ animation, preview }, node) => {
      animation.cancel();
      preview.remove();
      node.classList.remove('is-motion-landing');
    });
    landings.current.clear();
  }
  function animateLayout() {
    const previous = positions.current;
    positions.current = null;
    if (!previous) return;
    const elements = nodes();
    elements.forEach((node) => animations.current.get(node)?.cancel());
    animations.current.clear();
    clearLandings();
    if (reduced()) return;
    // Read all geometry before starting animations, including cards moved across parents.
    const layouts = elements.map((node) => ({ node, rect: node.getBoundingClientRect() }));
    layouts.forEach(({ node, rect }) => {
      const from = previous.get(node.dataset.workMotionItem!);
      if (!from || !rect.width || !rect.height) return;
      const scale = rect.width / node.offsetWidth || 1;
      const x = (from.left - rect.left) / scale,
        y = (from.top - rect.top) / scale;
      if (Math.abs(x) < 1 && Math.abs(y) < 1) return;
      if (parents.current.get(node.dataset.workMotionItem!) !== node.parentElement) {
        // A floating copy can cross scroll containers without being clipped by them.
        const preview = clone(node);
        preview.classList.add('work-item-landing-preview');
        preview.style.transform = `translate(${rect.left / scale}px, ${rect.top / scale}px)`;
        document.body.append(preview);
        node.classList.add('is-motion-landing');
        const animation = preview.animate(
          [
            {
              transform: `translate(${from.left / scale}px, ${from.top / scale}px)`,
              rotate: '1.25deg',
              scale: '1.02',
            },
            {
              transform: `translate(${rect.left / scale}px, ${rect.top / scale}px)`,
              rotate: '0deg',
              scale: '1',
            },
          ],
          { duration: 360, easing },
        );
        landings.current.set(node, { preview, animation });
        animation.onfinish = () => {
          preview.remove();
          node.classList.remove('is-motion-landing');
          landings.current.delete(node);
          if (node.isConnected)
            node.animate(
              [
                { boxShadow: '0 0 0 2px var(--system-accent)' },
                { boxShadow: '0 0 0 0 transparent' },
              ],
              { duration: 400, easing },
            );
        };
        return;
      }
      const animation = node.animate(
        [{ transform: `translate(${x}px, ${y}px)` }, { transform: 'translate(0, 0)' }],
        { duration: 320, easing },
      );
      animations.current.set(node, animation);
      animation.onfinish = () => {
        if (animations.current.get(node) === animation) animations.current.delete(node);
      };
    });
  }
  function clearTarget() {
    const current = drag.current;
    if (!current) return;
    capture();
    current.marker.remove();
    current.column?.classList.remove('is-drag-over', 'is-backlog-drop-target');
    current.column = null;
    current.target = null;
    animateLayout();
  }
  function clearDrag(animate = true) {
    const current = drag.current;
    if (!current) return;
    if (animate) capture();
    cancelAnimationFrame(frame.current);
    current.preview.remove();
    current.image.remove();
    current.marker.remove();
    current.source.classList.remove('is-dragging');
    current.column?.classList.remove('is-drag-over', 'is-backlog-drop-target');
    drag.current = null;
    if (animate) animateLayout();
  }
  function movePreview() {
    const current = drag.current;
    if (!current) return;
    const rect = current.source.getBoundingClientRect();
    const x = Math.max(8, Math.min(current.x - current.offsetX, innerWidth - rect.width - 8));
    const y = Math.max(8, Math.min(current.y - current.offsetY, innerHeight - rect.height - 8));
    current.preview.style.transform = `translate3d(${x / current.scale}px, ${y / current.scale}px, 0)`;
  }
  function positionTarget(column: HTMLElement) {
    const current = drag.current;
    if (!current) return;
    const list = column.querySelector<HTMLElement>('.tasks-issue-list');
    const group = column.dataset.workDropGroup!;
    const markerBounds = current.marker.getBoundingClientRect();
    if (
      current.column === column &&
      current.marker.isConnected &&
      current.y >= markerBounds.top &&
      current.y <= markerBounds.bottom
    )
      return;
    const cards = [...(list?.querySelectorAll<HTMLElement>(itemSelector) || [])].filter(
      (node) => node !== current.source,
    );
    const index = cards.findIndex((node) => {
      const bounds = node.getBoundingClientRect();
      return current.y < bounds.top + bounds.height / 2;
    });
    const insertion = index < 0 ? cards.length : index;
    const before = cards[insertion] || null,
      after = cards[insertion - 1] || null;
    const target = {
      group,
      before: before ? Number(before.dataset.workMotionItem) : null,
      after: after ? Number(after.dataset.workMotionItem) : null,
    };
    if (
      current.target?.group === group &&
      current.target.before === target.before &&
      current.target.after === target.after
    )
      return;
    capture();
    current.column?.classList.remove('is-drag-over', 'is-backlog-drop-target');
    current.column = column;
    current.target = target;
    column.classList.add(data.view === 'board' ? 'is-drag-over' : 'is-backlog-drop-target');
    if (list) {
      const samePlace =
        current.source.parentElement === list &&
        cards
          .slice(0, insertion)
          .every(
            (node) =>
              !!(node.compareDocumentPosition(current.source) & Node.DOCUMENT_POSITION_FOLLOWING),
          ) &&
        cards
          .slice(insertion)
          .every(
            (node) =>
              !!(current.source.compareDocumentPosition(node) & Node.DOCUMENT_POSITION_FOLLOWING),
          );
      if (samePlace) current.marker.remove();
      else list.insertBefore(current.marker, before || list.querySelector('.work-backlog-create'));
    } else current.marker.remove();
    animateLayout();
  }
  function tick() {
    const current = drag.current;
    if (!current) return;
    movePreview();
    const column = document
      .elementFromPoint(current.x, current.y)
      ?.closest<HTMLElement>('[data-work-drop-group]');
    if (column && root.current?.contains(column)) {
      const list = column.querySelector<HTMLElement>('.tasks-issue-list');
      const board = column.closest<HTMLElement>('.tasks-kanban-board');
      const scrollArea =
        data.view === 'backlog' ? root.current?.closest<HTMLElement>('.work-content') : list;
      const speed = (point: number, start: number, end: number) => {
        const edge = Math.min(48, (end - start) / 4);
        return point < start + edge
          ? -10 * Math.max(0, 1 - (point - start) / edge)
          : point > end - edge
            ? 10 * Math.max(0, 1 - (end - point) / edge)
            : 0;
      };
      if (scrollArea) {
        const rect = scrollArea.getBoundingClientRect();
        scrollArea.scrollTop += speed(current.y, rect.top, rect.bottom);
      }
      if (board) {
        const rect = board.getBoundingClientRect();
        board.scrollLeft += speed(current.x, rect.left, rect.right);
      }
      positionTarget(column);
    } else if (current.target) clearTarget();
    frame.current = requestAnimationFrame(tick);
  }
  function start(event: DragEvent) {
    const source = event.currentTarget as HTMLElement;
    if (startedOnControl.current) {
      event.preventDefault();
      return false;
    }
    clearDrag(false);
    const rect = source.getBoundingClientRect();
    const preview = clone(source);
    const image = document.createElement('canvas');
    image.width = image.height = 1;
    image.className = 'work-board-native-drag-image';
    const marker = document.createElement('div');
    marker.className = 'work-item-drop-slot';
    marker.style.height = `${source.offsetHeight}px`;
    marker.setAttribute('aria-hidden', 'true');
    drag.current = {
      source,
      preview,
      image,
      marker,
      column: null,
      target: null,
      x: event.clientX,
      y: event.clientY,
      offsetX: event.clientX - rect.left,
      offsetY: event.clientY - rect.top,
      scale: rect.width / source.offsetWidth || 1,
    };
    movePreview();
    document.body.append(preview, image);
    event.dataTransfer.setDragImage(image, 0, 0);
    // Changing the source before the native snapshot can cancel the browser's drag.
    frame.current = requestAnimationFrame(() => {
      source.classList.add('is-dragging');
      tick();
    });
    return true;
  }
  function pointerDown(event: PointerEvent) {
    // Native dragstart targets the draggable article, even when pressed on its button.
    startedOnControl.current = !!(event.target as Element).closest(
      'button, input, select, textarea, [role="menu"]',
    );
  }
  function over(event: DragEvent) {
    const current = drag.current;
    if (!current) return;
    const column = (event.target as Element).closest<HTMLElement>('[data-work-drop-group]');
    if (!column || !root.current?.contains(column)) return;
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
    current.x = event.clientX;
    current.y = event.clientY;
    positionTarget(column);
  }
  function prepareDrop() {
    const current = drag.current;
    capture();
    if (current && !reduced()) {
      positions.current?.set(
        current.source.dataset.workMotionItem!,
        current.preview.getBoundingClientRect(),
      );
      parents.current.set(current.source.dataset.workMotionItem!, null);
    }
    clearDrag(false);
  }
  useLayoutEffect(() => {
    root.current
      ?.querySelectorAll<HTMLElement>(`${itemSelector} a, ${itemSelector} img`)
      .forEach((node) => {
        node.draggable = false;
      });
    animateLayout();
  }, [data]);
  useEffect(() => {
    const move = (event: globalThis.DragEvent) => {
      if (drag.current && (event.clientX || event.clientY)) {
        drag.current.x = event.clientX;
        drag.current.y = event.clientY;
      }
    };
    const end = () => {
      if (drag.current) {
        clearDrag();
        cancel.current();
      }
    };
    const key = (event: KeyboardEvent) => {
      if (event.key === 'Escape') end();
    };
    document.addEventListener('dragover', move);
    document.addEventListener('dragend', end);
    document.addEventListener('keydown', key);
    window.addEventListener('blur', end);
    return () => {
      clearDrag(false);
      animations.current.forEach((animation) => animation.cancel());
      clearLandings();
      document.removeEventListener('dragover', move);
      document.removeEventListener('dragend', end);
      document.removeEventListener('keydown', key);
      window.removeEventListener('blur', end);
    };
  }, []);
  return {
    root,
    start,
    over,
    pointerDown,
    clearDrag,
    capture,
    prepareDrop,
    target: () => drag.current?.target,
  };
}
