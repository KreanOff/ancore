import {
  useEffect,
  useLayoutEffect,
  useRef,
  useState,
  type KeyboardEvent,
  type PointerEvent,
  type RefObject,
} from 'react';
import { NODE_HEIGHT, NODE_WIDTH, type Position } from './workflow-board';
import {
  fitWorkflow,
  screenToWorld,
  zoomWorkflowAt,
  type WorkflowCamera,
} from './workflow-viewport';

type Gesture =
  | { kind: 'pan'; id: number; start: Position; camera: WorkflowCamera }
  | { kind: 'pinch'; ids: number[]; distance: number; anchor: Position; camera: WorkflowCamera };
const midpoint = (a: Position, b: Position) => ({ x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 });
const distance = (a: Position, b: Position) => Math.max(1, Math.hypot(a.x - b.x, a.y - b.y));

/** Camera movement is view state: it never edits or saves the workflow draft. */
export function useWorkflowCamera(
  viewport: RefObject<HTMLDivElement>,
  nodes: readonly Position[],
  cancelNodeDrag: () => void,
) {
  const [camera, setCamera] = useState<WorkflowCamera>({ x: 0, y: 0, zoom: 1 });
  const [viewportSize, setViewportSize] = useState({ width: 0, height: 0 });
  const cameraRef = useRef(camera);
  const latest = useRef({ nodes, cancelNodeDrag });
  latest.current = { nodes, cancelNodeDrag };
  const [panning, setPanning] = useState(false);
  const [hand, setHand] = useState(false);
  const handRef = useRef(false);
  const gesture = useRef<Gesture | null>(null);
  const originalCamera = useRef<WorkflowCamera | null>(null);
  const pointers = useRef(new Map<number, Position>());
  const suppressClick = useRef(false);

  function update(next: WorkflowCamera) {
    cameraRef.current = next;
    setCamera(next);
  }
  function point(event: { clientX: number; clientY: number }): Position {
    const element = viewport.current!;
    const rect = element.getBoundingClientRect();
    return {
      x: ((event.clientX - rect.left) * element.clientWidth) / rect.width,
      y: ((event.clientY - rect.top) * element.clientHeight) / rect.height,
    };
  }
  function center() {
    return {
      x: (viewport.current?.clientWidth || 0) / 2,
      y: (viewport.current?.clientHeight || 0) / 2,
    };
  }
  function fit() {
    const element = viewport.current;
    if (!element?.clientWidth || !element.clientHeight) return;
    latest.current.cancelNodeDrag();
    update(
      fitWorkflow(latest.current.nodes, {
        width: element.clientWidth,
        height: element.clientHeight,
      }),
    );
  }
  function panTo(point: Position) {
    const middle = center();
    update({
      ...cameraRef.current,
      x: middle.x - point.x * cameraRef.current.zoom,
      y: middle.y - point.y * cameraRef.current.zoom,
    });
  }
  function centerOn(node: Position) {
    panTo({ x: node.x + NODE_WIDTH / 2, y: node.y + NODE_HEIGHT / 2 });
  }
  function reveal(node: Position) {
    const element = viewport.current;
    if (!element || gesture.current) return;
    const active = cameraRef.current;
    const left = node.x * active.zoom + active.x;
    const top = node.y * active.zoom + active.y;
    // Include the connection button and the start-of-process label.
    if (
      left < 24 ||
      top < 32 ||
      left + NODE_WIDTH * active.zoom + 24 > element.clientWidth ||
      top + NODE_HEIGHT * active.zoom + 24 > element.clientHeight
    )
      centerOn(node);
  }
  function zoomTo(nextZoom: number, anchor = center()) {
    latest.current.cancelNodeDrag();
    update(zoomWorkflowAt(cameraRef.current, nextZoom, anchor));
  }
  function cancel() {
    if (originalCamera.current) update(originalCamera.current);
    if (gesture.current) suppressClick.current = true;
    gesture.current = null;
    originalCamera.current = null;
    pointers.current.clear();
    setPanning(false);
  }
  useLayoutEffect(() => {
    const element = viewport.current;
    if (!element) return;
    let previous = { width: 0, height: 0 };
    const observer = new ResizeObserver(() => {
      const size = { width: element.clientWidth, height: element.clientHeight };
      if (!size.width || !size.height) return;
      setViewportSize(size);
      if (!previous.width) {
        const fitted = fitWorkflow(latest.current.nodes, size);
        // Keep the opening view legible; Fit is available for large maps.
        const zoom = Math.max(0.65, fitted.zoom);
        const anchor = screenToWorld({ x: size.width / 2, y: size.height / 2 }, fitted);
        update({ x: size.width / 2 - anchor.x * zoom, y: size.height / 2 - anchor.y * zoom, zoom });
      } else {
        // Resizing the map or rotating the device keeps the same world center.
        update({
          ...cameraRef.current,
          x: cameraRef.current.x + (size.width - previous.width) / 2,
          y: cameraRef.current.y + (size.height - previous.height) / 2,
        });
      }
      previous = size;
    });
    observer.observe(element);
    return () => observer.disconnect();
  }, []);
  useEffect(() => {
    const element = viewport.current;
    if (!element) return;
    const wheel = (event: WheelEvent) => {
      event.preventDefault();
      if (gesture.current) return;
      const units = event.deltaMode === 1 ? 16 : event.deltaMode === 2 ? element.clientHeight : 1;
      const delta = Math.max(-240, Math.min(240, event.deltaY * units));
      if (event.shiftKey) update({ ...cameraRef.current, x: cameraRef.current.x - delta });
      else
        zoomTo(
          cameraRef.current.zoom * Math.exp(-delta * (event.ctrlKey ? 0.01 : 0.002)),
          point(event),
        );
    };
    const releaseSpace = (event: globalThis.KeyboardEvent) => {
      if (event.code === 'Space') {
        handRef.current = false;
        setHand(false);
      }
    };
    const blur = () => {
      handRef.current = false;
      setHand(false);
      cancel();
      latest.current.cancelNodeDrag();
    };
    element.addEventListener('wheel', wheel, { passive: false });
    window.addEventListener('keyup', releaseSpace);
    window.addEventListener('blur', blur);
    return () => {
      element.removeEventListener('wheel', wheel);
      window.removeEventListener('keyup', releaseSpace);
      window.removeEventListener('blur', blur);
    };
  }, []);

  function down(event: PointerEvent<HTMLDivElement>) {
    if (!pointers.current.size) suppressClick.current = false;
    if (event.pointerType !== 'touch' && event.button !== 0 && event.button !== 1) return;
    const location = point(event);
    const interactive = (event.target as Element).closest(
      'button, input, select, textarea, a, .work-flow-edge-hit',
    );
    if (event.pointerType === 'touch') pointers.current.set(event.pointerId, location);
    if (event.pointerType === 'touch' && pointers.current.size >= 2) {
      event.preventDefault();
      event.stopPropagation();
      latest.current.cancelNodeDrag();
      const entries = [...pointers.current.entries()].slice(0, 2);
      originalCamera.current ??= cameraRef.current;
      gesture.current = {
        kind: 'pinch',
        ids: entries.map(([id]) => id),
        distance: distance(entries[0][1], entries[1][1]),
        anchor: screenToWorld(midpoint(entries[0][1], entries[1][1]), cameraRef.current),
        camera: cameraRef.current,
      };
      suppressClick.current = true;
      setPanning(true);
      event.currentTarget.setPointerCapture(event.pointerId);
      return;
    }
    if (interactive && !handRef.current && event.button !== 1) return;
    event.preventDefault();
    event.stopPropagation();
    latest.current.cancelNodeDrag();
    pointers.current.set(event.pointerId, location);
    originalCamera.current = cameraRef.current;
    gesture.current = {
      kind: 'pan',
      id: event.pointerId,
      start: location,
      camera: cameraRef.current,
    };
    setPanning(true);
    event.currentTarget.focus({ preventScroll: true });
    event.currentTarget.setPointerCapture(event.pointerId);
  }
  function move(event: PointerEvent<HTMLDivElement>) {
    if (pointers.current.has(event.pointerId)) pointers.current.set(event.pointerId, point(event));
    const active = gesture.current;
    if (!active) return;
    event.preventDefault();
    event.stopPropagation();
    if (active.kind === 'pan') {
      if (active.id !== event.pointerId) return;
      const location = point(event),
        dx = location.x - active.start.x,
        dy = location.y - active.start.y;
      if (Math.abs(dx) + Math.abs(dy) < 3 && !suppressClick.current) return;
      suppressClick.current = true;
      update({ ...active.camera, x: active.camera.x + dx, y: active.camera.y + dy });
    } else {
      const a = pointers.current.get(active.ids[0]),
        b = pointers.current.get(active.ids[1]);
      if (!a || !b) return;
      const middle = midpoint(a, b);
      const zoom = zoomWorkflowAt(
        active.camera,
        (active.camera.zoom * distance(a, b)) / active.distance,
        middle,
      ).zoom;
      update({ x: middle.x - active.anchor.x * zoom, y: middle.y - active.anchor.y * zoom, zoom });
    }
  }
  function up(event: PointerEvent<HTMLDivElement>) {
    pointers.current.delete(event.pointerId);
    const active = gesture.current;
    if (!active) return;
    event.stopPropagation();
    if (pointers.current.size && event.pointerType === 'touch') {
      const [id, location] = [...pointers.current.entries()][0];
      gesture.current = { kind: 'pan', id, start: location, camera: cameraRef.current };
    } else {
      gesture.current = null;
      originalCamera.current = null;
      setPanning(false);
    }
  }
  function keyDown(event: KeyboardEvent<HTMLDivElement>) {
    if ((event.target as Element).closest('input, textarea, select, [contenteditable="true"]'))
      return;
    if (event.key === 'Escape') {
      cancel();
      return;
    }
    if (event.code === 'Space') {
      event.preventDefault();
      handRef.current = true;
      setHand(true);
      return;
    }
    if (event.target !== event.currentTarget || event.ctrlKey || event.metaKey || event.altKey)
      return;
    const step = event.shiftKey ? 160 : 40;
    if (['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown'].includes(event.key)) {
      event.preventDefault();
      update({
        ...cameraRef.current,
        x:
          cameraRef.current.x +
          (event.key === 'ArrowLeft' ? step : event.key === 'ArrowRight' ? -step : 0),
        y:
          cameraRef.current.y +
          (event.key === 'ArrowUp' ? step : event.key === 'ArrowDown' ? -step : 0),
      });
    } else if (event.key === 'Home') {
      event.preventDefault();
      fit();
    } else if (['+', '=', '-', '0'].includes(event.key)) {
      event.preventDefault();
      zoomTo(event.key === '0' ? 1 : cameraRef.current.zoom * (event.key === '-' ? 0.8 : 1.25));
    }
  }
  return {
    camera,
    viewportSize,
    panning,
    hand,
    fit,
    centerOn,
    panTo,
    reveal,
    zoomTo,
    cancel,
    worldPoint: (event: { clientX: number; clientY: number }) =>
      screenToWorld(point(event), cameraRef.current),
    centerWorld: () => screenToWorld(center(), cameraRef.current),
    handlers: {
      onPointerDownCapture: down,
      onPointerMoveCapture: move,
      onPointerUpCapture: up,
      onPointerCancelCapture: (event: PointerEvent<HTMLDivElement>) => {
        if (gesture.current) {
          event.stopPropagation();
          cancel();
        } else pointers.current.delete(event.pointerId);
      },
      onLostPointerCapture: (event: PointerEvent<HTMLDivElement>) => {
        if (
          event.target === event.currentTarget &&
          gesture.current &&
          pointers.current.has(event.pointerId)
        )
          cancel();
      },
      onClickCapture: (event: React.MouseEvent<HTMLDivElement>) => {
        if (suppressClick.current && event.detail > 0) {
          event.preventDefault();
          event.stopPropagation();
          suppressClick.current = false;
        }
      },
      onKeyDownCapture: keyDown,
      onAuxClick: (event: React.MouseEvent<HTMLDivElement>) => {
        if (event.button === 1) event.preventDefault();
      },
    },
  };
}
